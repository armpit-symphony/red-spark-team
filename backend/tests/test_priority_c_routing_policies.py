import os
from uuid import uuid4

import pytest
import requests
from dotenv import load_dotenv


load_dotenv("/app/frontend/.env")

BACKEND_PATH_PREFIX = os.environ.get("REACT_APP_BACKEND_URL")
if not BACKEND_PATH_PREFIX:
    raise RuntimeError("REACT_APP_BACKEND_URL is required for API testing.")


def resolve_base_url() -> str:
    if BACKEND_PATH_PREFIX.startswith("http"):
        base = BACKEND_PATH_PREFIX.rstrip("/")
        return base if base.endswith("/api") else f"{base}/api"
    return f"http://127.0.0.1:3000{BACKEND_PATH_PREFIX}".rstrip("/")


BASE_URL = resolve_base_url()


@pytest.fixture
def api_client():
    session = requests.Session()
    session.headers.update({"Content-Type": "application/json"})
    return session


def create_test_run(api_client):
    target_payload = {
        "name": f"TEST_RoutingTarget_{uuid4().hex[:8]}",
        "target_type": "webapp",
        "locator": f"https://routing-{uuid4().hex[:6]}.example.internal",
        "scope_limit": "TEST_Routing policy validation only.",
        "allowed_modes": ["exploratory"],
        "notes": "TEST_Target for routing policy checks",
    }
    target = api_client.post(f"{BASE_URL}/targets", json=target_payload).json()
    run_payload = {
        "target_id": target["id"],
        "mode": "exploratory",
        "objective": "TEST_Routing fallback behavior",
        "scope_notes": "TEST_Verify policy selection and error messaging",
        "consent_token": "",
    }
    return api_client.post(f"{BASE_URL}/runs", json=run_payload).json()["run"]["id"]


def backup_provider(api_client, provider_name):
    providers = api_client.get(f"{BASE_URL}/providers").json()
    provider = next((item for item in providers if item["provider"] == provider_name), None)
    assert provider is not None
    return {
        "provider": provider_name,
        "payload": {
            "model": provider["model"],
            "enabled": provider["enabled"],
            "auth_mode": provider["auth_mode"],
            "base_url": provider.get("base_url", ""),
            "custom_api_key": "",
        },
    }


def test_routing_policy_catalog_and_default_update(api_client):
    response = api_client.get(f"{BASE_URL}/routing-policies")
    assert response.status_code == 200
    payload = response.json()

    assert payload["default_policy_id"]
    assert len(payload["policies"]) >= 3
    assert {policy["id"] for policy in payload["policies"]} >= {"reliable-default", "openrouter-reliable", "minimax-reliable"}

    restore_default = payload["default_policy_id"]
    try:
        update = api_client.put(f"{BASE_URL}/routing-policies/default", json={"default_policy_id": "openrouter-reliable"})
        assert update.status_code == 200
        assert update.json()["default_policy_id"] == "openrouter-reliable"
    finally:
        api_client.put(f"{BASE_URL}/routing-policies/default", json={"default_policy_id": restore_default})


def test_routing_policy_fallback_error_reports_primary_and_fallback_reasons(api_client):
    run_id = create_test_run(api_client)
    openrouter_backup = backup_provider(api_client, "openrouter")
    openai_backup = backup_provider(api_client, "openai")

    try:
        api_client.put(
            f"{BASE_URL}/providers/openrouter",
            json={**openrouter_backup["payload"], "enabled": False},
        )
        api_client.put(
            f"{BASE_URL}/providers/openai",
            json={**openai_backup["payload"], "enabled": False},
        )

        response = api_client.post(
            f"{BASE_URL}/runs/{run_id}/analysis",
            json={
                "provider": "openai",
                "model": "gpt-5.2",
                "analysis_type": "report_draft",
                "focus": "TEST_Routing fallback errors",
                "routing_policy_id": "openrouter-reliable",
            },
        )
        assert response.status_code == 400
        detail = response.json()["detail"]
        assert "Primary route openrouter:openai/gpt-4.1-mini error" in detail
        assert "Fallback route openai:gpt-5.2 error" in detail
    finally:
        api_client.put(f"{BASE_URL}/providers/openrouter", json=openrouter_backup["payload"])
        api_client.put(f"{BASE_URL}/providers/openai", json=openai_backup["payload"])