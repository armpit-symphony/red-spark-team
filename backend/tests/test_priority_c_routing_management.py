import os

import pytest
import requests
from dotenv import load_dotenv


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


def test_routing_policy_update_and_telemetry_endpoint(api_client):
    state = api_client.get(f"{BASE_URL}/routing-policies")
    assert state.status_code == 200
    reliable_default = next(policy for policy in state.json()["policies"] if policy["id"] == "reliable-default")

    update_payload = {
        "label": "Reliable Default Edited",
        "goal": "balanced",
        "primary_provider": reliable_default["primary"]["provider"],
        "primary_model": reliable_default["primary"]["model"],
        "fallback_provider": reliable_default["fallback"]["provider"],
        "fallback_model": reliable_default["fallback"]["model"],
    }

    try:
        update = api_client.put(f"{BASE_URL}/routing-policies/reliable-default", json=update_payload)
        assert update.status_code == 200
        updated = update.json()
        assert updated["label"] == "Reliable Default Edited"
        assert updated["goal"] == "balanced"
        assert updated["source"] == "user"

        telemetry = api_client.get(f"{BASE_URL}/routing-policies/reliable-default/telemetry", params={"window": 25})
        assert telemetry.status_code == 200
        payload = telemetry.json()
        assert payload["policy_id"] == "reliable-default"
        assert payload["window"] == 25
        assert len(payload["candidate_summaries"]) == 2
        assert payload["preferred_route"]["provider"]
        assert payload["backup_route"]["provider"]
    finally:
        api_client.put(
            f"{BASE_URL}/routing-policies/reliable-default",
            json={
                "label": reliable_default["label"],
                "goal": reliable_default["goal"],
                "primary_provider": reliable_default["primary"]["provider"],
                "primary_model": reliable_default["primary"]["model"],
                "fallback_provider": reliable_default["fallback"]["provider"],
                "fallback_model": reliable_default["fallback"]["model"],
            },
        )