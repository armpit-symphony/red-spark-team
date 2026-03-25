import json
import os
from uuid import uuid4

import pytest
import requests
from dotenv import load_dotenv
from pymongo import MongoClient


load_dotenv("/app/frontend/.env")
load_dotenv("/app/backend/.env")

BACKEND_PATH_PREFIX = os.environ.get("REACT_APP_BACKEND_URL")
MONGO_URL = os.environ.get("MONGO_URL")
DB_NAME = os.environ.get("DB_NAME")

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
    """Shared API client for provider security, scanner import, and report approval/export flows."""
    session = requests.Session()
    session.headers.update({"Content-Type": "application/json"})
    return session


@pytest.fixture
def mongo_db():
    """Mongo fixture used only for encrypted key storage verification."""
    if not MONGO_URL or not DB_NAME:
        pytest.skip("MONGO_URL/DB_NAME missing; cannot verify encrypted storage.")
    client = MongoClient(MONGO_URL)
    db = client[DB_NAME]
    yield db
    client.close()


def provider_backup_for(api_client, provider_name: str):
    """Backup provider config and restore after mutation tests."""
    response = api_client.get(f"{BASE_URL}/providers")
    assert response.status_code == 200
    providers = response.json()
    target = next((item for item in providers if item["provider"] == provider_name), None)
    if not target:
        pytest.skip(f"{provider_name} provider not available in current seed data")

    return {
        "provider": target["provider"],
        "payload": {
            "model": target["model"],
            "enabled": target["enabled"],
            "auth_mode": target["auth_mode"],
            "base_url": target.get("base_url", ""),
            "custom_api_key": "",
        },
        "had_custom_key": bool(target.get("has_custom_key")),
    }


def create_test_run(api_client):
    """Create TEST_ target and run for scanner import and report workflow checks."""
    target_payload = {
        "name": f"TEST_ImportTarget_{uuid4().hex[:8]}",
        "target_type": "webapp",
        "locator": f"https://test-{uuid4().hex[:6]}.example.internal",
        "scope_limit": "TEST_Scope limited to authorized security review.",
        "allowed_modes": ["exploratory"],
        "notes": "TEST_Target for scanner import/report approval tests",
    }
    target_response = api_client.post(f"{BASE_URL}/targets", json=target_payload)
    assert target_response.status_code == 200
    target = target_response.json()

    run_payload = {
        "target_id": target["id"],
        "mode": "exploratory",
        "objective": "TEST_Validate import normalization and report approval flow",
        "scope_notes": "TEST_Use imported scanner output only",
        "consent_token": "",
    }
    run_response = api_client.post(f"{BASE_URL}/runs", json=run_payload)
    assert run_response.status_code == 200
    run_bundle = run_response.json()
    return run_bundle["run"]["id"]


@pytest.mark.parametrize("provider_name", ["openai", "anthropic", "openrouter"])
def test_provider_custom_key_save_is_encrypted_and_remove_works(api_client, mongo_db, provider_name):
    """Settings module: OpenAI, Anthropic, and OpenRouter custom key save/remove plus encrypted-at-rest verification."""
    provider_backup = provider_backup_for(api_client, provider_name)
    test_key = f"TEST_PROVIDER_KEY_{uuid4().hex}"

    try:
        save_payload = {
            **provider_backup["payload"],
            "auth_mode": "custom",
            "enabled": True,
            "custom_api_key": test_key,
        }
        save_response = api_client.put(f"{BASE_URL}/providers/{provider_name}", json=save_payload)
        assert save_response.status_code == 200
        saved = save_response.json()

        assert saved["provider"] == provider_name
        assert saved["has_custom_key"] is True
        assert saved["key_last4"] == test_key[-4:]
        assert saved["status"] == "ready"
        assert "custom_api_key" not in saved
        assert "encrypted_custom_api_key" not in saved

        db_provider = mongo_db.providers.find_one({"provider": provider_name}, {"_id": 0})
        assert isinstance(db_provider.get("encrypted_custom_api_key", ""), str)
        assert len(db_provider.get("encrypted_custom_api_key", "")) > 20
        assert db_provider.get("encrypted_custom_api_key") != test_key
        assert (db_provider.get("custom_api_key") or "") == ""

        remove_response = api_client.delete(f"{BASE_URL}/providers/{provider_name}/custom-key")
        assert remove_response.status_code == 200
        removed = remove_response.json()
        assert removed["has_custom_key"] is False
        assert removed["key_last4"] == ""

        db_provider_removed = mongo_db.providers.find_one({"provider": provider_name}, {"_id": 0})
        assert "encrypted_custom_api_key" not in db_provider_removed
    finally:
        api_client.put(f"{BASE_URL}/providers/{provider_backup['provider']}", json=provider_backup["payload"])
        if not provider_backup["had_custom_key"]:
            api_client.delete(f"{BASE_URL}/providers/{provider_backup['provider']}/custom-key")


def test_scanner_import_text_normalizes_findings_and_skips_invalid_items(api_client):
    """Scanner import module: text import creates normalized findings and skips invalid blocks."""
    run_id = create_test_run(api_client)
    text_payload = {
        "source_name": "TEST_TextScanner",
        "import_format": "text",
        "content": (
            "Title: Open admin console exposed\n"
            "Severity: High\n"
            "Evidence: Admin endpoint responds without auth.\n\n"
            "Title: Missing severity only\n"
            "Evidence: This block should be skipped due to missing severity.\n\n"
            "Title: Verbose stack trace disclosure\n"
            "Severity: medium\n"
            "Evidence: Application returns stack traces in 500 responses."
        ),
    }

    import_response = api_client.post(f"{BASE_URL}/runs/{run_id}/scanner-import", json=text_payload)
    assert import_response.status_code == 200
    payload = import_response.json()
    summary = payload["summary"]

    assert summary["imported_count"] == 2
    assert summary["skipped_count"] == 1
    assert summary["detected_count"] == 3
    assert "Block 2" in summary["skipped_items"][0]

    run_detail = api_client.get(f"{BASE_URL}/runs/{run_id}")
    assert run_detail.status_code == 200
    findings = [item for item in run_detail.json()["findings"] if item.get("source_name") == "TEST_TextScanner"]
    assert len(findings) == 2
    assert all(item["severity"] in {"critical", "high", "medium", "low"} for item in findings)
    assert all(item["import_format"] == "text" for item in findings)


def test_scanner_import_json_normalizes_findings_and_skips_invalid_items(api_client):
    """Scanner import module: JSON import creates normalized findings and skips invalid items."""
    run_id = create_test_run(api_client)
    json_content = [
        {
            "title": "Public storage bucket listing",
            "severity": "Critical",
            "description": "Bucket listing exposed without access controls",
        },
        {
            "title": "Missing severity item should skip",
            "description": "No risk level provided",
        },
        {
            "name": "CSRF token missing",
            "risk": "high",
            "details": "Sensitive action endpoint lacks anti-CSRF check",
        },
    ]
    json_payload = {
        "source_name": "TEST_JsonScanner",
        "import_format": "json",
        "content": json.dumps(json_content),
    }

    import_response = api_client.post(f"{BASE_URL}/runs/{run_id}/scanner-import", json=json_payload)
    assert import_response.status_code == 200
    payload = import_response.json()
    summary = payload["summary"]

    assert summary["imported_count"] == 2
    assert summary["skipped_count"] == 1
    assert summary["detected_count"] == 3
    assert "Item 2" in summary["skipped_items"][0]

    run_detail = api_client.get(f"{BASE_URL}/runs/{run_id}")
    assert run_detail.status_code == 200
    findings = [item for item in run_detail.json()["findings"] if item.get("source_name") == "TEST_JsonScanner"]
    assert len(findings) == 2
    assert all(item["severity"] in {"critical", "high", "medium", "low"} for item in findings)
    assert all(item["import_format"] == "json" for item in findings)


def test_report_pending_to_approved_and_export_markdown_workflow(api_client):
    """Report workflow module: approval transition, export guard, and markdown export contract."""
    run_id = create_test_run(api_client)
    analysis_payload = {
        "provider": "openai",
        "model": "gpt-5.2",
        "analysis_type": "report_draft",
        "focus": "TEST_Generate markdown report for approval/export workflow validation",
    }
    analysis_response = api_client.post(f"{BASE_URL}/runs/{run_id}/analysis", json=analysis_payload, timeout=120)
    assert analysis_response.status_code == 200
    bundle = analysis_response.json()
    report = bundle.get("report")

    assert report is not None
    assert report["review_status"] == "pending_review"
    assert report["can_export"] is False

    blocked_export = api_client.get(f"{BASE_URL}/reports/{report['id']}/export")
    assert blocked_export.status_code == 400
    assert "approved" in blocked_export.json().get("detail", "").lower()

    approve_response = api_client.post(f"{BASE_URL}/reports/{report['id']}/approve", json={})
    assert approve_response.status_code == 200
    approved_report = approve_response.json()
    assert approved_report["review_status"] == "approved"
    assert approved_report["can_export"] is True

    export_response = api_client.get(f"{BASE_URL}/reports/{report['id']}/export")
    assert export_response.status_code == 200
    exported = export_response.json()
    assert exported["filename"].endswith(".md")
    assert isinstance(exported["markdown"], str)
    assert len(exported["markdown"]) > 20

    run_detail = api_client.get(f"{BASE_URL}/runs/{run_id}")
    assert run_detail.status_code == 200
    detail_report = run_detail.json()["report"]
    assert detail_report["review_status"] == "approved"
    assert detail_report["can_export"] is True


def test_openrouter_model_catalog_loads_and_manual_refresh_works(api_client):
    """Model catalog module: OpenRouter catalog is readable and manual refresh returns entries."""
    catalog_response = api_client.get(f"{BASE_URL}/model-catalog", params={"provider": "openrouter"})
    assert catalog_response.status_code == 200
    catalog = catalog_response.json()

    assert catalog["provider"] == "openrouter"
    assert isinstance(catalog["models"], list)
    assert catalog["model_count"] >= 1
    assert catalog["refresh_status"] in {"ok", "fallback"}
    assert catalog["source"] in {"openrouter_models_api", "manual_fallback"}

    refresh_response = api_client.post(f"{BASE_URL}/model-catalog/refresh", json={"provider": "openrouter"})
    assert refresh_response.status_code == 200
    refreshed = refresh_response.json()

    assert refreshed["provider"] == "openrouter"
    assert refreshed["model_count"] >= 1
    assert isinstance(refreshed["models"], list)
    assert refreshed["refresh_status"] in {"ok", "fallback"}