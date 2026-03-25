import json
import os
from uuid import uuid4

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
    """Shared JSON session for model catalog and core workflow regression checks."""
    session = requests.Session()
    session.headers.update({"Content-Type": "application/json"})
    return session


@pytest.fixture
def created_run(api_client):
    """Create TEST_ target/run so scanner import flow can be validated without UI dependency."""
    target_payload = {
        "name": f"TEST_PB_Target_{uuid4().hex[:8]}",
        "target_type": "webapp",
        "locator": f"https://priority-b-{uuid4().hex[:6]}.example.internal",
        "scope_limit": "TEST_Priority B scoped integration testing.",
        "allowed_modes": ["exploratory"],
        "notes": "TEST_Target for Priority B regression checks",
    }
    target_response = api_client.post(f"{BASE_URL}/targets", json=target_payload)
    assert target_response.status_code == 200
    target = target_response.json()

    run_payload = {
        "target_id": target["id"],
        "mode": "exploratory",
        "objective": "TEST_Priority B regression run",
        "scope_notes": "TEST_Focus on model catalog and scanner import stability",
        "consent_token": "",
    }
    run_response = api_client.post(f"{BASE_URL}/runs", json=run_payload)
    assert run_response.status_code == 200
    bundle = run_response.json()
    return bundle["run"]["id"]


def test_providers_load_for_settings_cards(api_client):
    """Settings module: provider cards source API returns expected provider objects."""
    response = api_client.get(f"{BASE_URL}/providers")
    assert response.status_code == 200
    providers = response.json()

    assert isinstance(providers, list)
    assert len(providers) >= 4
    assert all("provider" in provider and "model" in provider for provider in providers)


def test_openrouter_catalog_load_endpoint(api_client):
    """Model catalog module: GET endpoint returns OpenRouter catalog and health metadata."""
    response = api_client.get(f"{BASE_URL}/model-catalog", params={"provider": "openrouter"})
    assert response.status_code == 200
    payload = response.json()

    assert payload["provider"] == "openrouter"
    assert isinstance(payload["models"], list)
    assert payload["model_count"] >= 1
    assert payload["model_count"] == len(payload["models"])
    assert payload["refresh_status"] in {"ok", "fallback"}
    assert payload["source"] in {"openrouter_models_api", "manual_fallback"}


def test_openrouter_manual_refresh_endpoint(api_client):
    """Model catalog module: POST refresh endpoint works and returns refreshed model list."""
    response = api_client.post(f"{BASE_URL}/model-catalog/refresh", json={"provider": "openrouter"})
    assert response.status_code == 200
    payload = response.json()

    assert payload["provider"] == "openrouter"
    assert isinstance(payload["models"], list)
    assert payload["model_count"] >= 1
    assert payload["model_count"] == len(payload["models"])
    assert payload["refresh_status"] in {"ok", "fallback"}
    assert payload["source"] in {"openrouter_models_api", "manual_fallback"}


def test_openrouter_catalog_source_meta_is_healthy(api_client):
    """Model catalog module: fallback-safe metadata shape stays healthy for operators."""
    response = api_client.get(f"{BASE_URL}/model-catalog", params={"provider": "openrouter"})
    assert response.status_code == 200
    payload = response.json()

    assert payload.get("last_refreshed_at")
    assert payload.get("source") in {"openrouter_models_api", "manual_fallback"}
    assert payload.get("refresh_status") in {"ok", "fallback"}

    if payload.get("refresh_status") == "fallback":
        assert isinstance(payload.get("last_error", ""), str)


def test_existing_import_flow_still_works(created_run, api_client):
    """Regression module: scanner import normalization flow remains intact after catalog additions."""
    payload = {
        "source_name": "TEST_PB_JSON",
        "import_format": "json",
        "content": json.dumps(
            [
                {"title": "TEST_Open admin route", "severity": "high", "description": "Admin route exposed"},
                {"title": "TEST_Missing severity should skip", "description": "No severity"},
            ]
        ),
    }

    response = api_client.post(f"{BASE_URL}/runs/{created_run}/scanner-import", json=payload)
    assert response.status_code == 200
    result = response.json()["summary"]

    assert result["imported_count"] == 1
    assert result["skipped_count"] == 1
    assert result["detected_count"] == 2

    detail_response = api_client.get(f"{BASE_URL}/runs/{created_run}")
    assert detail_response.status_code == 200
    findings = [item for item in detail_response.json()["findings"] if item.get("source_name") == "TEST_PB_JSON"]
    assert len(findings) == 1
    assert findings[0]["title"] == "TEST_Open admin route"