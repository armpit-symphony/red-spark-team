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
    # In this environment, frontend proxy serves relative /api paths.
    return f"http://127.0.0.1:3000{BACKEND_PATH_PREFIX}".rstrip("/")


BASE_URL = resolve_base_url()


@pytest.fixture
def api_client():
    """Shared JSON API session for core platform endpoint verification."""
    session = requests.Session()
    session.headers.update({"Content-Type": "application/json"})
    return session


@pytest.fixture
def created_target(api_client):
    """Target CRUD setup for runs and policy-gated workflow validation."""
    payload = {
        "name": f"TEST_Target_{uuid4().hex[:8]}",
        "target_type": "webapp",
        "locator": f"https://test-{uuid4().hex[:6]}.internal.example",
        "scope_limit": "TEST_Only passive review over authorized internal pages.",
        "allowed_modes": ["exploratory"],
        "notes": "TEST_Target for integration checks.",
    }
    response = api_client.post(f"{BASE_URL}/targets", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == payload["name"]
    assert data["allowed_modes"] == payload["allowed_modes"]
    assert isinstance(data["id"], str)
    return data


@pytest.fixture
def created_run(api_client, created_target):
    """Run lifecycle setup for run detail, section save, and analysis flow checks."""
    payload = {
        "target_id": created_target["id"],
        "mode": "exploratory",
        "objective": "TEST_Verify governed exploratory workflow end-to-end.",
        "scope_notes": "TEST_Boundary is passive checks only.",
        "consent_token": "",
    }
    response = api_client.post(f"{BASE_URL}/runs", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["run"]["target_id"] == created_target["id"]
    assert data["run"]["objective"] == payload["objective"]
    assert isinstance(data["tasks"], list)
    return data


def test_health(api_client):
    """Health endpoint baseline validation."""
    response = api_client.get(f"{BASE_URL}/health")
    assert response.status_code == 200
    assert response.json().get("status") == "ok"


def test_overview_loads_stats_and_charts(api_client):
    """Overview dashboard API data and chart payload validation."""
    response = api_client.get(f"{BASE_URL}/overview")
    assert response.status_code == 200
    data = response.json()
    assert set(data["stats"].keys()) == {"targets", "runs", "findings", "reports"}
    assert isinstance(data["severity_chart"], list)
    assert isinstance(data["run_volume_chart"], list)


def test_targets_create_and_list(api_client, created_target):
    """Target creation persistence check using create then list pattern."""
    list_response = api_client.get(f"{BASE_URL}/targets")
    assert list_response.status_code == 200
    targets = list_response.json()
    matched = [item for item in targets if item["id"] == created_target["id"]]
    assert len(matched) == 1
    assert matched[0]["name"] == created_target["name"]


def test_policies_page_save_persists(api_client):
    """Policy save round-trip validation for governance controls."""
    current_response = api_client.get(f"{BASE_URL}/policies")
    assert current_response.status_code == 200
    current = current_response.json()

    updated_payload = {
        "passive_rules": current["passive_rules"] + ["TEST_Policy line"],
        "deep_mode_requirements": current["deep_mode_requirements"],
        "deep_mode_consent_token": current["deep_mode_consent_token"],
        "export_requires_review": current["export_requires_review"],
        "secret_redaction_enabled": current["secret_redaction_enabled"],
        "deny_by_default_egress": current["deny_by_default_egress"],
    }
    update_response = api_client.put(f"{BASE_URL}/policies", json=updated_payload)
    assert update_response.status_code == 200
    assert "TEST_Policy line" in update_response.json()["passive_rules"]

    verify_response = api_client.get(f"{BASE_URL}/policies")
    assert verify_response.status_code == 200
    assert "TEST_Policy line" in verify_response.json()["passive_rules"]


def test_create_exploratory_run_and_detail(api_client, created_run):
    """Run creation and detail endpoint validation."""
    run_id = created_run["run"]["id"]
    detail_response = api_client.get(f"{BASE_URL}/runs/{run_id}")
    assert detail_response.status_code == 200
    detail = detail_response.json()
    assert detail["run"]["id"] == run_id
    assert isinstance(detail["sections"], list)
    assert any(section["section_key"] == "report-draft" for section in detail["sections"])


def test_evidence_section_edit_and_save(api_client, created_run):
    """Evidence section upsert persistence check with follow-up detail retrieval."""
    run_id = created_run["run"]["id"]
    payload = {
        "section_key": "tool-output",
        "title": "Tool Output",
        "content": "TEST_Updated scanner output evidence block.",
        "format": "text",
    }
    update_response = api_client.post(f"{BASE_URL}/runs/{run_id}/sections", json=payload)
    assert update_response.status_code == 200

    detail_response = api_client.get(f"{BASE_URL}/runs/{run_id}")
    assert detail_response.status_code == 200
    sections = detail_response.json()["sections"]
    tool_section = next((item for item in sections if item["section_key"] == "tool-output"), None)
    assert tool_section is not None
    assert tool_section["content"] == payload["content"]


def test_openai_report_draft_generation(api_client, created_run):
    """LLM provider integration validation for OpenAI report drafting."""
    run_id = created_run["run"]["id"]
    payload = {
        "provider": "openai",
        "model": "gpt-5.2",
        "analysis_type": "report_draft",
        "focus": "TEST_Check concise governance-focused report output.",
    }
    response = api_client.post(f"{BASE_URL}/runs/{run_id}/analysis", json=payload, timeout=90)
    assert response.status_code == 200
    data = response.json()
    report_section = next((item for item in data["sections"] if item["section_key"] == "report-draft"), None)
    assert report_section is not None
    assert isinstance(report_section["content"], str)
    assert len(report_section["content"]) > 20


def test_reports_page_returns_generated_report(api_client, created_run):
    """Reports registry verification after report draft generation."""
    run_id = created_run["run"]["id"]
    analysis_payload = {
        "provider": "openai",
        "model": "gpt-5.2",
        "analysis_type": "report_draft",
        "focus": "TEST_Ensure report appears in reports listing.",
    }
    analyze_response = api_client.post(f"{BASE_URL}/runs/{run_id}/analysis", json=analysis_payload, timeout=90)
    assert analyze_response.status_code == 200

    reports_response = api_client.get(f"{BASE_URL}/reports")
    assert reports_response.status_code == 200
    reports = reports_response.json()
    matched = [item for item in reports if item["audit_run_id"] == run_id]
    assert len(matched) >= 1
    assert isinstance(matched[0]["markdown"], str)
    assert len(matched[0]["markdown"]) > 20


def test_settings_provider_load_and_save(api_client):
    """Provider settings load and save cycle validation."""
    providers_response = api_client.get(f"{BASE_URL}/providers")
    assert providers_response.status_code == 200
    providers = providers_response.json()
    openai_provider = next((item for item in providers if item["provider"] == "openai"), None)
    assert openai_provider is not None

    payload = {
        "model": openai_provider["model"],
        "enabled": openai_provider["enabled"],
        "auth_mode": openai_provider["auth_mode"],
        "base_url": openai_provider.get("base_url", ""),
        "custom_api_key": "",
    }
    update_response = api_client.put(f"{BASE_URL}/providers/openai", json=payload)
    assert update_response.status_code == 200
    saved = update_response.json()
    assert saved["provider"] == "openai"
    assert saved["model"] == payload["model"]


def test_audit_log_entries_load(api_client):
    """Audit log feed retrieval validation."""
    response = api_client.get(f"{BASE_URL}/audit-log")
    assert response.status_code == 200
    entries = response.json()
    assert isinstance(entries, list)
    assert len(entries) >= 1
    assert {"id", "action", "details", "created_at"}.issubset(entries[0].keys())
