import os

import pytest
import requests
from dotenv import load_dotenv


# Priority C module: editable routing policy persistence + last-25 telemetry summary.
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


def test_routing_policy_edit_persists_label_goal_primary_and_fallback(api_client):
    state_response = api_client.get(f"{BASE_URL}/routing-policies")
    assert state_response.status_code == 200
    state_payload = state_response.json()
    policy = next(item for item in state_payload["policies"] if item["id"] == "reliable-default")

    original = {
        "label": policy["label"],
        "goal": policy["goal"],
        "primary_provider": policy["primary"]["provider"],
        "primary_model": policy["primary"]["model"],
        "fallback_provider": policy["fallback"]["provider"],
        "fallback_model": policy["fallback"]["model"],
    }

    edited = {
        "label": "Reliable Default Iter5",
        "goal": "cost_first",
        "primary_provider": "minimax",
        "primary_model": "MiniMax-Text-01",
        "fallback_provider": "openai",
        "fallback_model": "gpt-5.2",
    }

    try:
        update_response = api_client.put(f"{BASE_URL}/routing-policies/reliable-default", json=edited)
        assert update_response.status_code == 200
        updated = update_response.json()

        assert updated["label"] == edited["label"]
        assert updated["goal"] == edited["goal"]
        assert updated["primary"]["provider"] == edited["primary_provider"]
        assert updated["primary"]["model"] == edited["primary_model"]
        assert updated["fallback"]["provider"] == edited["fallback_provider"]
        assert updated["fallback"]["model"] == edited["fallback_model"]

        verify_state = api_client.get(f"{BASE_URL}/routing-policies")
        assert verify_state.status_code == 200
        reloaded = next(item for item in verify_state.json()["policies"] if item["id"] == "reliable-default")
        assert reloaded["label"] == edited["label"]
        assert reloaded["goal"] == edited["goal"]
        assert reloaded["primary"]["provider"] == edited["primary_provider"]
        assert reloaded["primary"]["model"] == edited["primary_model"]
        assert reloaded["fallback"]["provider"] == edited["fallback_provider"]
        assert reloaded["fallback"]["model"] == edited["fallback_model"]
    finally:
        api_client.put(f"{BASE_URL}/routing-policies/reliable-default", json=original)


def test_routing_policy_telemetry_uses_last_25_window_and_route_summaries(api_client):
    telemetry_response = api_client.get(
        f"{BASE_URL}/routing-policies/reliable-default/telemetry",
        params={"window": 25},
    )
    assert telemetry_response.status_code == 200
    telemetry = telemetry_response.json()

    assert telemetry["policy_id"] == "reliable-default"
    assert telemetry["window"] == 25
    assert isinstance(telemetry["candidate_summaries"], list)
    assert len(telemetry["candidate_summaries"]) == 2
    assert telemetry["preferred_route"]["provider"]
    assert telemetry["preferred_route"]["model"]
    assert telemetry["backup_route"]["provider"]
    assert telemetry["backup_route"]["model"]
