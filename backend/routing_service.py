from pathlib import Path
from typing import Any

import yaml

from database import clean_document
from models import now_iso


ROUTING_CONFIG_PATH = Path("/app/configs/routing.yaml")
ROUTING_SETTINGS_ID = "default-routing-settings"
ROUTING_MEMORY_WINDOW = 25
DEFAULT_ROUTING_POLICIES = [
    {
        "id": "reliable-default",
        "label": "Reliable Default",
        "description": "Use OpenAI first, then try Anthropic once if the primary route fails.",
        "goal": "reliability_first",
        "primary": {"provider": "openai", "model": "gpt-5.2"},
        "fallback": {"provider": "anthropic", "model": "claude-sonnet-4-5-20250929"},
    },
    {
        "id": "openrouter-reliable",
        "label": "OpenRouter First",
        "description": "Use OpenRouter first, then try OpenAI once if the primary route fails.",
        "goal": "reliability_first",
        "primary": {"provider": "openrouter", "model": "openai/gpt-4.1-mini"},
        "fallback": {"provider": "openai", "model": "gpt-5.2"},
    },
    {
        "id": "minimax-reliable",
        "label": "MiniMax First",
        "description": "Use MiniMax first, then try Anthropic once if the primary route fails.",
        "goal": "reliability_first",
        "primary": {"provider": "minimax", "model": "MiniMax-Text-01"},
        "fallback": {"provider": "anthropic", "model": "claude-sonnet-4-5-20250929"},
    },
]


def _normalize_candidate(candidate: dict[str, Any]) -> dict[str, str]:
    return {
        "provider": str(candidate["provider"]),
        "model": str(candidate["model"]),
    }


def _build_policy_record(policy: dict[str, Any], source: str) -> dict[str, Any]:
    return {
        "id": policy["id"],
        "label": policy["label"],
        "description": policy.get("description", ""),
        "goal": policy.get("goal", "reliability_first"),
        "source": source,
        "primary": _normalize_candidate(policy["primary"]),
        "fallback": _normalize_candidate(policy["fallback"]),
        "updated_at": now_iso(),
    }


def load_routing_policies() -> list[dict[str, Any]]:
    try:
        payload = yaml.safe_load(ROUTING_CONFIG_PATH.read_text()) if ROUTING_CONFIG_PATH.exists() else {}
        payload = payload or {}
        policies = payload.get("routing_policies") or DEFAULT_ROUTING_POLICIES
    except Exception:  # noqa: BLE001
        policies = DEFAULT_ROUTING_POLICIES

    return [_build_policy_record(policy, "config") for policy in policies]


async def sync_routing_policies(database):
    policies = load_routing_policies()
    policy_ids = []

    for policy in policies:
        policy_ids.append(policy["id"])
        existing = clean_document(await database.routing_policies.find_one({"id": policy["id"]}, {"_id": 0}))
        if not existing:
            await database.routing_policies.insert_one(policy)

    existing_settings = clean_document(await database.routing_settings.find_one({"id": ROUTING_SETTINGS_ID}, {"_id": 0}))
    default_policy_id = existing_settings.get("default_policy_id") if existing_settings else "direct"
    valid_policy_ids = {policy["id"] for policy in policies}
    if default_policy_id != "direct" and default_policy_id not in valid_policy_ids:
        default_policy_id = policy_ids[0] if policy_ids else "direct"

    await database.routing_settings.update_one(
        {"id": ROUTING_SETTINGS_ID},
        {"$set": {"id": ROUTING_SETTINGS_ID, "default_policy_id": default_policy_id, "updated_at": now_iso()}},
        upsert=True,
    )


async def get_routing_state(database) -> dict[str, Any]:
    policies = [clean_document(item) async for item in database.routing_policies.find({}, {"_id": 0}).sort("label", 1)]
    settings = clean_document(await database.routing_settings.find_one({"id": ROUTING_SETTINGS_ID}, {"_id": 0})) or {
        "default_policy_id": "direct"
    }
    return {"default_policy_id": settings.get("default_policy_id", "direct"), "policies": policies}


async def get_candidate_cost_units(database, candidate: dict[str, str]) -> float:
    static_cost_units = {
        ("openai", "gpt-5.2"): 5.0,
        ("anthropic", "claude-sonnet-4-5-20250929"): 4.0,
        ("minimax", "MiniMax-Text-01"): 2.0,
    }
    if candidate["provider"] == "openrouter":
        model = clean_document(
            await database.model_catalog.find_one({"provider": "openrouter", "model_id": candidate["model"]}, {"_id": 0})
        )
        if model:
            pricing = model.get("pricing") or {}
            try:
                prompt = float(pricing.get("prompt") or 0)
                completion = float(pricing.get("completion") or 0)
                cost = prompt + completion
                if cost > 0:
                    return round(cost * 1_000_000, 4)
            except (TypeError, ValueError):
                return 3.0
        return 3.0

    return static_cost_units.get((candidate["provider"], candidate["model"]), 3.5)


async def get_candidate_telemetry_summary(database, candidate: dict[str, str], window: int = ROUTING_MEMORY_WINDOW) -> dict[str, Any]:
    traces = [
        clean_document(item)
        async for item in database.routing_traces.find(
            {"selected_provider": candidate["provider"], "selected_model": candidate["model"]},
            {"_id": 0},
        )
        .sort("created_at", -1)
        .limit(window)
    ]

    total_attempts = len(traces)
    successful_attempts = [trace for trace in traces if trace.get("success")]
    fallback_attempts = [trace for trace in traces if trace.get("used_as_fallback")]
    fallback_successes = [trace for trace in fallback_attempts if trace.get("success")]
    avg_latency_ms = round(sum(trace.get("latency_ms", 0) for trace in successful_attempts) / len(successful_attempts), 2) if successful_attempts else 1500.0
    success_rate = round(len(successful_attempts) / total_attempts, 4) if total_attempts else 1.0
    fallback_success_rate = round(len(fallback_successes) / len(fallback_attempts), 4) if fallback_attempts else success_rate
    cost_units = await get_candidate_cost_units(database, candidate)

    return {
        "provider": candidate["provider"],
        "model": candidate["model"],
        "total_attempts": total_attempts,
        "success_rate": success_rate,
        "fallback_success_rate": fallback_success_rate,
        "avg_latency_ms": avg_latency_ms,
        "cost_units": cost_units,
    }


def score_candidate(goal: str, summary: dict[str, Any], configured_rank: int) -> float:
    latency_component = 1 / (1 + (summary["avg_latency_ms"] / 1000))
    cost_component = 1 / (1 + summary["cost_units"])
    success_component = summary["success_rate"]
    fallback_component = summary["fallback_success_rate"]
    configured_bias = 0.01 if configured_rank == 0 else 0.0

    if goal == "latency_first":
        return round((latency_component * 0.45) + (success_component * 0.3) + (fallback_component * 0.15) + (cost_component * 0.1) + configured_bias, 6)
    if goal == "cost_first":
        return round((cost_component * 0.45) + (success_component * 0.25) + (fallback_component * 0.15) + (latency_component * 0.15) + configured_bias, 6)
    if goal == "balanced":
        return round((success_component * 0.3) + (fallback_component * 0.2) + (latency_component * 0.25) + (cost_component * 0.25) + configured_bias, 6)
    return round((success_component * 0.4) + (fallback_component * 0.3) + (latency_component * 0.2) + (cost_component * 0.1) + configured_bias, 6)


async def get_policy_telemetry(database, policy_id: str, window: int = ROUTING_MEMORY_WINDOW) -> dict[str, Any] | None:
    policy = clean_document(await database.routing_policies.find_one({"id": policy_id}, {"_id": 0}))
    if not policy:
        return None

    configured_candidates = [policy["primary"], policy["fallback"]]
    candidate_summaries = []
    for index, candidate in enumerate(configured_candidates):
        summary = await get_candidate_telemetry_summary(database, candidate, window)
        summary["configured_role"] = "primary" if index == 0 else "fallback"
        summary["score"] = score_candidate(policy["goal"], summary, index)
        candidate_summaries.append(summary)

    ranked_candidates = sorted(candidate_summaries, key=lambda item: item["score"], reverse=True)
    recent_traces = [
        clean_document(item)
        async for item in database.routing_traces.find({"routing_policy_id": policy_id}, {"_id": 0}).sort("created_at", -1).limit(window)
    ]

    return {
        "policy_id": policy_id,
        "label": policy["label"],
        "goal": policy["goal"],
        "window": window,
        "preferred_route": ranked_candidates[0],
        "backup_route": ranked_candidates[1],
        "candidate_summaries": ranked_candidates,
        "recent_traces": recent_traces,
    }