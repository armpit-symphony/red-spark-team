from typing import Any

import httpx

from models import now_iso


OPENROUTER_MODELS_URL = "https://openrouter.ai/api/v1/models"
OPENROUTER_FALLBACK_MODELS = [
    {
        "id": "openai/gpt-4.1-mini",
        "name": "GPT-4.1 Mini",
        "description": "Balanced OpenRouter fallback model for fast reasoning and drafting.",
        "context_length": 1047576,
        "pricing": {"prompt": "0.0000004", "completion": "0.0000016"},
    },
    {
        "id": "google/gemini-2.0-flash-001",
        "name": "Gemini 2.0 Flash",
        "description": "Fast multimodal-capable OpenRouter model with broad availability.",
        "context_length": 1048576,
        "pricing": {"prompt": "0.0000001", "completion": "0.0000004"},
    },
    {
        "id": "anthropic/claude-3.7-sonnet",
        "name": "Claude 3.7 Sonnet",
        "description": "High-quality reasoning model available through OpenRouter.",
        "context_length": 200000,
        "pricing": {"prompt": "0.000003", "completion": "0.000015"},
    },
    {
        "id": "meta-llama/llama-3.1-70b-instruct",
        "name": "Llama 3.1 70B Instruct",
        "description": "Open-weight fallback option for general analysis tasks.",
        "context_length": 131072,
        "pricing": {"prompt": "0.00000088", "completion": "0.00000088"},
    },
]


def normalize_openrouter_model(item: dict[str, Any], source: str) -> dict[str, Any]:
    pricing = item.get("pricing") or {}
    top_provider = item.get("top_provider") or {}

    return {
        "provider": "openrouter",
        "model_id": item["id"],
        "name": item.get("name") or item["id"],
        "description": item.get("description", ""),
        "context_length": item.get("context_length") or top_provider.get("context_length") or 0,
        "pricing": {
            "prompt": pricing.get("prompt", ""),
            "completion": pricing.get("completion", ""),
        },
        "source": source,
        "supported_parameters": item.get("supported_parameters", []),
        "updated_at": now_iso(),
    }


async def refresh_openrouter_catalog(database) -> dict[str, Any]:
    source = "manual_fallback"
    error = ""

    try:
        async with httpx.AsyncClient(timeout=20) as client:
            response = await client.get(OPENROUTER_MODELS_URL)
            response.raise_for_status()
            payload = response.json()
            raw_models = payload.get("data") or []
            models = [normalize_openrouter_model(item, "openrouter_models_api") for item in raw_models if item.get("id")]
            source = "openrouter_models_api"
    except Exception as exc:  # noqa: BLE001
        error = str(exc)
        models = [normalize_openrouter_model(item, "manual_fallback") for item in OPENROUTER_FALLBACK_MODELS]

    models = sorted(models, key=lambda item: item["name"].lower())
    refreshed_at = now_iso()

    await database.model_catalog.delete_many({"provider": "openrouter"})
    if models:
        await database.model_catalog.insert_many(models)

    meta = {
        "provider": "openrouter",
        "model_count": len(models),
        "last_refreshed_at": refreshed_at,
        "source": source,
        "refresh_status": "fallback" if source == "manual_fallback" else "ok",
        "last_error": error,
        "updated_at": refreshed_at,
    }
    await database.model_catalog_meta.update_one({"provider": "openrouter"}, {"$set": meta}, upsert=True)
    return meta