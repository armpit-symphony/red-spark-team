import os
from uuid import uuid4

import pytest
import requests
from dotenv import load_dotenv


# Priority C routing regression: direct/manual mode analysis must still work.
load_dotenv("/app/frontend/.env")

BACKEND_BASE = os.environ.get("REACT_APP_BACKEND_URL")
if not BACKEND_BASE:
    raise RuntimeError("REACT_APP_BACKEND_URL is required for API testing.")


def resolve_base_url() -> str:
    base = BACKEND_BASE.rstrip("/")
    if base.startswith("http"):
        return base if base.endswith("/api") else f"{base}/api"
    return f"http://127.0.0.1:3000{base}".rstrip("/")


BASE_URL = resolve_base_url()


@pytest.fixture
def api_client():
    session = requests.Session()
    session.headers.update({"Content-Type": "application/json"})
    return session


def create_test_run(api_client):
    target_payload = {
        "name": f"TEST_DirectModeTarget_{uuid4().hex[:8]}",
        "target_type": "webapp",
        "locator": f"https://direct-mode-{uuid4().hex[:6]}.example.internal",
        "scope_limit": "TEST_Direct mode regression only.",
        "allowed_modes": ["exploratory"],
        "notes": "TEST_Target for direct routing regression",
    }
    target_response = api_client.post(f"{BASE_URL}/targets", json=target_payload)
    assert target_response.status_code == 200
    target = target_response.json()

    run_payload = {
        "target_id": target["id"],
        "mode": "exploratory",
        "objective": "TEST_Direct mode analysis",
        "scope_notes": "TEST_Verify direct/manual mode still works",
        "consent_token": "",
    }
    run_response = api_client.post(f"{BASE_URL}/runs", json=run_payload)
    assert run_response.status_code == 200
    return run_response.json()["run"]["id"]


def test_analysis_direct_mode_still_works(api_client):
    providers_response = api_client.get(f"{BASE_URL}/providers")
    assert providers_response.status_code == 200
    enabled_providers = [item for item in providers_response.json() if item.get("enabled")]
    if not enabled_providers:
        pytest.skip("No enabled provider available for direct mode analysis test.")

    selected = enabled_providers[0]
    run_id = create_test_run(api_client)
    analysis_payload = {
        "provider": selected["provider"],
        "model": selected["model"],
        "analysis_type": "finding_summary",
        "focus": "TEST_direct mode route trace",
        "routing_policy_id": "direct",
    }
    response = api_client.post(f"{BASE_URL}/runs/{run_id}/analysis", json=analysis_payload, timeout=120)
    assert response.status_code == 200
    payload = response.json()

    route = payload.get("last_analysis_route") or {}
    assert route.get("mode") == "direct"
    assert route.get("routing_policy_id") == "direct"
    assert route.get("selected_provider") == selected["provider"]
    assert route.get("selected_model") == selected["model"]
    assert route.get("used_fallback") is False
