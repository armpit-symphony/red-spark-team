from pathlib import Path
from typing import Any

import yaml

from database import clean_document
from models import now_iso


ROUTING_CONFIG_PATH = Path("/app/configs/routing.yaml")
ROUTING_SETTINGS_ID = "default-routing-settings"


def _normalize_candidate(candidate: dict[str, Any]) -> dict[str, str]:
    return {
        "provider": str(candidate["provider"]),
        "model": str(candidate["model"]),
    }


def load_routing_policies() -> list[dict[str, Any]]:
    payload = yaml.safe_load(ROUTING_CONFIG_PATH.read_text()) or {}
    policies = payload.get("routing_policies") or []
    now = now_iso()
    normalized = []

    for policy in policies:
        normalized.append(
            {
                "id": policy["id"],
                "label": policy["label"],
                "description": policy.get("description", ""),
                "goal": policy.get("goal", "reliability_first"),
                "source": "config",
                "primary": _normalize_candidate(policy["primary"]),
                "fallback": _normalize_candidate(policy["fallback"]),
                "updated_at": now,
            }
        )

    return normalized


async def sync_routing_policies(database):
    policies = load_routing_policies()
    policy_ids = []

    for policy in policies:
        policy_ids.append(policy["id"])
        await database.routing_policies.update_one({"id": policy["id"]}, {"$set": policy}, upsert=True)

    if policy_ids:
        await database.routing_policies.delete_many({"source": "config", "id": {"$nin": policy_ids}})

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