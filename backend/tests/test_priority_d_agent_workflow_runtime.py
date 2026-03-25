import os
import time
from uuid import uuid4

import pytest
import requests
from dotenv import load_dotenv
from requests import RequestException


# Priority D multi-agent runtime: workflow sequencing, handoffs, stored outputs, and report workspace updates.
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
KNOWN_WORKFLOW_RUN_ID = "3df373f0-8ac1-4efb-82b6-07a0deb135db"


def api_call_with_retry(api_client, method: str, path: str, attempts: int = 4, **kwargs):
    last_error = None
    last_response = None
    for _ in range(attempts):
        try:
            response = api_client.request(method, f"{BASE_URL}{path}", **kwargs)
            last_response = response
            if response.status_code in {502, 503, 504}:
                last_error = RuntimeError(f"Transient upstream status {response.status_code}")
                time.sleep(1.5)
                continue
            return response
        except RequestException as exc:
            last_error = exc
            time.sleep(1.5)
    if last_response is not None:
        return last_response
    raise AssertionError(f"API call failed after retries for {method} {path}: {last_error}")


@pytest.fixture
def api_client():
    session = requests.Session()
    session.headers.update({"Content-Type": "application/json"})
    return session


def create_test_run(api_client, objective_suffix: str) -> str:
    target_payload = {
        "name": f"TEST_AgentTarget_{uuid4().hex[:8]}",
        "target_type": "webapp",
        "locator": f"https://agent-{uuid4().hex[:6]}.internal.example",
        "scope_limit": "TEST_Authorized internal app review only.",
        "allowed_modes": ["exploratory"],
        "notes": "TEST_target for Priority D multi-agent workflow verification",
    }
    target_response = api_call_with_retry(api_client, "POST", "/targets", json=target_payload, timeout=45)
    if target_response.status_code != 200:
        pytest.skip(f"Unable to create test target on public endpoint (status={target_response.status_code}).")
    target = target_response.json()

    run_payload = {
        "target_id": target["id"],
        "mode": "exploratory",
        "objective": f"TEST_PriorityD objective {objective_suffix}",
        "scope_notes": "TEST_Verify planner -> parallel -> reporter handoffs",
        "consent_token": "",
    }
    run_response = api_call_with_retry(api_client, "POST", "/runs", json=run_payload, timeout=45)
    if run_response.status_code != 200:
        pytest.skip(f"Unable to create test run on public endpoint (status={run_response.status_code}).")
    return run_response.json()["run"]["id"]


def skip_if_llm_runtime_blocked(response):
    if response.status_code == 200:
        return
    detail = ""
    try:
        detail = str(response.json().get("detail", ""))
    except Exception:  # noqa: BLE001
        detail = response.text
    lowered = detail.lower()
    if response.status_code in {400, 401, 429, 502, 503, 504} and (
        "budget has been exceeded" in lowered
        or "no api key" in lowered
        or "not responding" in lowered
        or "failed to generate chat completion" in lowered
    ):
        pytest.skip(f"LLM/runtime dependency blocked workflow execution: {detail}")


def enabled_provider_or_skip(api_client) -> tuple[str, str]:
    providers_response = api_call_with_retry(api_client, "GET", "/providers", timeout=45)
    assert providers_response.status_code == 200
    providers = providers_response.json()
    enabled = [item for item in providers if item.get("enabled")]
    if not enabled:
        pytest.skip("No enabled providers available for agent workflow runtime test.")
    return enabled[0]["provider"], enabled[0]["model"]


def test_agent_workflow_post_then_get_returns_completed_steps_with_handoffs_and_route_trace(api_client):
    run_id = create_test_run(api_client, objective_suffix=f"A_{uuid4().hex[:8]}")
    provider, model = enabled_provider_or_skip(api_client)

    workflow_payload = {
        "provider": provider,
        "model": model,
        "routing_policy_id": "direct",
        "focus": "TEST_PriorityD verify sequence and handoffs",
    }
    post_response = api_call_with_retry(api_client, "POST", f"/runs/{run_id}/agent-workflow", json=workflow_payload, timeout=180)
    skip_if_llm_runtime_blocked(post_response)
    assert post_response.status_code == 200
    workflow_result = post_response.json()

    workflow = workflow_result["workflow"]
    steps = workflow_result["steps"]
    assert workflow["audit_run_id"] == run_id
    assert workflow["status"] == "completed"
    assert workflow["parallel_groups"] == [["planner"], ["evidence_normalizer", "risk_reviewer"], ["reporter"]]
    assert len(steps) == 4

    step_by_key = {item["agent_key"]: item for item in steps}
    assert set(step_by_key.keys()) == {"planner", "evidence_normalizer", "risk_reviewer", "reporter"}
    assert step_by_key["planner"]["depends_on"] == []
    assert step_by_key["evidence_normalizer"]["depends_on"] == ["planner"]
    assert step_by_key["risk_reviewer"]["depends_on"] == ["planner"]
    assert step_by_key["reporter"]["depends_on"] == ["evidence_normalizer", "risk_reviewer"]

    for key in ["planner", "evidence_normalizer", "risk_reviewer", "reporter"]:
        step = step_by_key[key]
        assert step["status"] == "completed"
        assert isinstance(step.get("output", ""), str)
        assert len(step.get("output", "")) > 20
        assert isinstance(step.get("handoff_summary", ""), str)
        assert len(step.get("handoff_summary", "")) > 5
        assert isinstance(step.get("route_trace"), dict)
        assert step["route_trace"].get("selected_provider")
        assert step["route_trace"].get("selected_model")

    get_response = api_call_with_retry(api_client, "GET", f"/runs/{run_id}/agent-workflow", timeout=45)
    assert get_response.status_code == 200
    latest = get_response.json()
    assert latest["workflow"]["id"] == workflow["id"]
    assert len(latest["steps"]) == 4

    detail_response = api_call_with_retry(api_client, "GET", f"/runs/{run_id}", timeout=45)
    assert detail_response.status_code == 200
    detail = detail_response.json()
    section_by_key = {item["section_key"]: item for item in detail["sections"]}
    assert len(section_by_key["agent-plan"].get("content", "")) > 20
    assert len(section_by_key["normalized-evidence"].get("content", "")) > 20
    assert len(section_by_key["risk-review"].get("content", "")) > 20
    assert len(section_by_key["report-draft"].get("content", "")) > 20
    assert detail.get("report") is not None
    assert detail["report"]["review_status"] == "pending_review"
    assert len(detail["report"].get("markdown", "")) > 20


def test_agent_workflow_get_returns_latest_steps_and_handoff_fields_for_existing_run(api_client):
    response = api_call_with_retry(api_client, "GET", f"/runs/{KNOWN_WORKFLOW_RUN_ID}/agent-workflow", timeout=45)
    if response.status_code != 200:
        pytest.skip(f"Known workflow run not available (status={response.status_code}).")

    payload = response.json()
    workflow = payload.get("workflow")
    steps = payload.get("steps", [])
    if not workflow or not steps:
        pytest.skip("No persisted workflow found on known run id for GET regression validation.")

    assert workflow["audit_run_id"] == KNOWN_WORKFLOW_RUN_ID
    assert isinstance(steps, list)
    assert len(steps) == 4

    step_by_key = {item["agent_key"]: item for item in steps}
    for key in ["planner", "evidence_normalizer", "risk_reviewer", "reporter"]:
        assert key in step_by_key
        step = step_by_key[key]
        assert isinstance(step.get("status", ""), str)
        assert isinstance(step.get("depends_on", []), list)
        assert isinstance(step.get("handoff_summary", ""), str)

    reporter = step_by_key["reporter"]
    assert reporter["depends_on"] == ["evidence_normalizer", "risk_reviewer"]
    if reporter.get("status") == "completed":
        assert len(reporter.get("output", "")) > 20
    else:
        assert reporter.get("status") in {"queued", "running", "failed"}


def test_agent_workflow_current_run_memory_does_not_leak_other_run_objective_markers(api_client):
    foreign_marker = f"DO_NOT_LEAK_{uuid4().hex}"
    foreign_run_id = create_test_run(api_client, objective_suffix=foreign_marker)
    own_marker = f"ONLY_THIS_RUN_{uuid4().hex}"
    run_id = create_test_run(api_client, objective_suffix=own_marker)
    assert foreign_run_id != run_id

    provider, model = enabled_provider_or_skip(api_client)
    workflow_payload = {
        "provider": provider,
        "model": model,
        "routing_policy_id": "direct",
        "focus": f"TEST_Use marker {own_marker}",
    }
    post_response = api_call_with_retry(api_client, "POST", f"/runs/{run_id}/agent-workflow", json=workflow_payload, timeout=180)
    skip_if_llm_runtime_blocked(post_response)
    assert post_response.status_code == 200
    data = post_response.json()
    assert data["workflow"]["audit_run_id"] == run_id

    reporter_step = next(item for item in data["steps"] if item["agent_key"] == "reporter")
    assert foreign_marker not in reporter_step.get("output", "")
