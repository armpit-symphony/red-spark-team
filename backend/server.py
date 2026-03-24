from collections import Counter
from uuid import uuid4

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from database import clean_document, database
from llm_service import run_provider_analysis
from models import AnalysisRequest, PolicyUpdate, ProviderUpdate, RunCreate, SectionUpsert, TargetCreate, now_iso
from seed import seed_database


app = FastAPI(title="Unified Agentic Red-Team Audit Platform")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


async def log_event(action: str, details: str):
    await database.audit_logs.insert_one(
        {
            "id": str(uuid4()),
            "actor": "single-admin",
            "action": action,
            "details": details,
            "created_at": now_iso(),
        }
    )


async def get_run_bundle(run_id: str):
    run_record = clean_document(await database.runs.find_one({"id": run_id}, {"_id": 0}))
    if not run_record:
        raise HTTPException(status_code=404, detail="Run not found.")

    tasks = [clean_document(item) async for item in database.tasks.find({"audit_run_id": run_id}, {"_id": 0})]
    findings = [clean_document(item) async for item in database.findings.find({"audit_run_id": run_id}, {"_id": 0})]
    sections = [clean_document(item) async for item in database.artifacts.find({"audit_run_id": run_id}, {"_id": 0})]
    report = clean_document(await database.reports.find_one({"audit_run_id": run_id}, {"_id": 0}))
    return {"run": run_record, "tasks": tasks, "findings": findings, "sections": sections, "report": report}


@app.on_event("startup")
async def startup_event():
    await seed_database(database)


@app.get("/api/health")
async def health_check():
    return {"status": "ok"}


@app.get("/api/overview")
async def get_overview():
    targets = [clean_document(item) async for item in database.targets.find({}, {"_id": 0})]
    runs = [clean_document(item) async for item in database.runs.find({}, {"_id": 0})]
    findings = [clean_document(item) async for item in database.findings.find({}, {"_id": 0})]
    reports = [clean_document(item) async for item in database.reports.find({}, {"_id": 0})]
    logs = [clean_document(item) async for item in database.audit_logs.find({}, {"_id": 0}).sort("created_at", -1).limit(5)]

    severity_counts = Counter(finding["severity"] for finding in findings)
    run_volume = Counter(run["created_at"][:10] for run in runs)

    return {
        "stats": {
            "targets": len(targets),
            "runs": len(runs),
            "findings": len(findings),
            "reports": len(reports),
        },
        "severity_chart": [
            {"name": level.title(), "value": severity_counts.get(level, 0)}
            for level in ["critical", "high", "medium", "low"]
        ],
        "run_volume_chart": [
            {"day": day, "runs": total} for day, total in sorted(run_volume.items())
        ],
        "recent_logs": logs,
    }


@app.get("/api/targets")
async def get_targets():
    return [clean_document(item) async for item in database.targets.find({}, {"_id": 0}).sort("created_at", -1)]


@app.post("/api/targets")
async def create_target(payload: TargetCreate):
    record = payload.model_dump()
    if not record["allowed_modes"]:
        raise HTTPException(status_code=400, detail="At least one allowed mode is required.")

    document = {
        "id": str(uuid4()),
        **record,
        "created_at": now_iso(),
        "last_audit_at": "",
    }
    await database.targets.insert_one(document)
    await log_event("created-target", f"Added target {record['name']} with modes {', '.join(record['allowed_modes'])}.")
    return clean_document(document)


@app.get("/api/policies")
async def get_policies():
    record = clean_document(await database.policies.find_one({"id": "default-policy"}, {"_id": 0}))
    return record


@app.put("/api/policies")
async def update_policies(payload: PolicyUpdate):
    updated = {**payload.model_dump(), "id": "default-policy", "updated_at": now_iso()}
    await database.policies.update_one({"id": "default-policy"}, {"$set": updated}, upsert=True)
    await log_event("updated-policy", "Updated fail-closed, consent, and export gate policies.")
    return updated


@app.get("/api/providers")
async def get_providers():
    providers = []
    async for item in database.providers.find({}, {"_id": 0, "custom_api_key": 0}).sort("label", 1):
        providers.append(clean_document(item))
    return providers


@app.put("/api/providers/{provider_name}")
async def update_provider(provider_name: str, payload: ProviderUpdate):
    existing = clean_document(await database.providers.find_one({"provider": provider_name}, {"_id": 0}))
    if not existing:
        raise HTTPException(status_code=404, detail="Provider not found.")

    custom_api_key = payload.custom_api_key.strip()
    status = "ready" if payload.enabled else "disabled"
    if payload.auth_mode == "custom" and not custom_api_key and not existing.get("custom_api_key"):
        status = "custom-key-required"

    update_data = {
        "model": payload.model,
        "enabled": payload.enabled,
        "auth_mode": payload.auth_mode,
        "base_url": payload.base_url.strip(),
        "status": status,
        "updated_at": now_iso(),
    }
    if custom_api_key:
        update_data["custom_api_key"] = custom_api_key
        update_data["key_last4"] = custom_api_key[-4:]

    await database.providers.update_one({"provider": provider_name}, {"$set": update_data})
    await log_event("updated-provider", f"Updated {provider_name} provider settings.")
    response = clean_document(await database.providers.find_one({"provider": provider_name}, {"_id": 0, "custom_api_key": 0}))
    return response


@app.get("/api/runs")
async def get_runs():
    return [clean_document(item) async for item in database.runs.find({}, {"_id": 0}).sort("created_at", -1)]


@app.post("/api/runs")
async def create_run(payload: RunCreate):
    target = clean_document(await database.targets.find_one({"id": payload.target_id}, {"_id": 0}))
    if not target:
        raise HTTPException(status_code=404, detail="Target not found.")

    if payload.mode not in target["allowed_modes"]:
        raise HTTPException(status_code=400, detail="Requested mode is not allowed for this target.")

    policies = clean_document(await database.policies.find_one({"id": "default-policy"}, {"_id": 0}))
    if payload.mode == "consent_gated" and payload.consent_token != policies["deep_mode_consent_token"]:
        raise HTTPException(status_code=400, detail="Consent-gated mode requires the correct runtime consent token.")

    run_id = str(uuid4())
    run_document = {
        "id": run_id,
        "target_id": target["id"],
        "target_name": target["name"],
        "target_locator": target["locator"],
        "mode": payload.mode,
        "objective": payload.objective,
        "scope_notes": payload.scope_notes,
        "status": "running",
        "created_at": now_iso(),
        "updated_at": now_iso(),
    }
    await database.runs.insert_one(run_document)

    task_documents = [
        {
            "id": str(uuid4()),
            "audit_run_id": run_id,
            "title": title,
            "task_type": task_type,
            "status": "queued" if index else "completed",
            "output": output,
            "created_at": now_iso(),
        }
        for index, (title, task_type, output) in enumerate(
            [
                ("Policy gate validation", "policy_gate", "Scope allowlist confirmed and mode validated."),
                ("Technique planning", "planner", "Task plan prepared for manual evidence collection and LLM drafting."),
                ("Evidence packaging", "evidence_normalizer", "Waiting for pasted tool output and operator notes."),
                ("Report drafting", "reporter", "Ready after evidence sections are saved or LLM draft is requested."),
            ]
        )
    ]
    await database.tasks.insert_many(task_documents)

    default_sections = [
        ("scope-brief", "Scope Brief", payload.scope_notes or target["scope_limit"]),
        ("tool-output", "Tool Output", "Paste scanner summaries, notes, or code review excerpts here."),
        ("evidence-pack", "Evidence Pack", "Paste normalized evidence, screenshots references, or log snippets here."),
        ("report-draft", "Report Draft", "Use the LLM analysis controls to generate a report draft here."),
    ]
    await database.artifacts.insert_many(
        [
            {
                "id": str(uuid4()),
                "audit_run_id": run_id,
                "section_key": key,
                "title": title,
                "content": content,
                "format": "markdown" if key == "report-draft" else "text",
                "created_at": now_iso(),
                "updated_at": now_iso(),
            }
            for key, title, content in default_sections
        ]
    )

    await database.targets.update_one({"id": target["id"]}, {"$set": {"last_audit_at": now_iso()}})
    await log_event("created-run", f"Started {payload.mode} run for {target['name']}.")
    return await get_run_bundle(run_id)


@app.get("/api/runs/{run_id}")
async def get_run_detail(run_id: str):
    return await get_run_bundle(run_id)


@app.post("/api/runs/{run_id}/sections")
async def upsert_section(run_id: str, payload: SectionUpsert):
    existing = clean_document(await database.runs.find_one({"id": run_id}, {"_id": 0}))
    if not existing:
        raise HTTPException(status_code=404, detail="Run not found.")

    section = {
        "id": str(uuid4()),
        "audit_run_id": run_id,
        "section_key": payload.section_key,
        "title": payload.title,
        "content": payload.content,
        "format": payload.format,
        "created_at": now_iso(),
        "updated_at": now_iso(),
    }
    await database.artifacts.update_one(
        {"audit_run_id": run_id, "section_key": payload.section_key},
        {"$set": section},
        upsert=True,
    )
    await database.runs.update_one({"id": run_id}, {"$set": {"updated_at": now_iso()}})
    await log_event("updated-section", f"Saved section {payload.title} for run {run_id}.")
    return await get_run_bundle(run_id)


@app.post("/api/runs/{run_id}/analysis")
async def analyze_run(run_id: str, payload: AnalysisRequest):
    bundle = await get_run_bundle(run_id)
    provider = clean_document(await database.providers.find_one({"provider": payload.provider}, {"_id": 0}))
    if not provider:
        raise HTTPException(status_code=404, detail="Provider not configured.")
    if not provider.get("enabled"):
        raise HTTPException(status_code=400, detail="Selected provider is disabled in settings.")

    provider["model"] = payload.model

    try:
        content = await run_provider_analysis(provider, bundle["run"], bundle["sections"], payload.analysis_type, payload.focus)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    section_key = payload.analysis_type.replace("_", "-")
    await database.artifacts.update_one(
        {"audit_run_id": run_id, "section_key": section_key},
        {
            "$set": {
                "id": str(uuid4()),
                "audit_run_id": run_id,
                "section_key": section_key,
                "title": payload.analysis_type.replace("_", " ").title(),
                "content": content,
                "format": "markdown",
                "created_at": now_iso(),
                "updated_at": now_iso(),
            }
        },
        upsert=True,
    )

    if payload.analysis_type == "report_draft":
        await database.reports.update_one(
            {"audit_run_id": run_id},
            {
                "$set": {
                    "id": str(uuid4()),
                    "audit_run_id": run_id,
                    "title": f"{bundle['run']['target_name']} Review Draft",
                    "executive_summary": content.split("\n", 1)[0][:220],
                    "markdown": content,
                    "review_status": "human-review-required",
                    "created_at": now_iso(),
                    "updated_at": now_iso(),
                }
            },
            upsert=True,
        )
        await database.runs.update_one({"id": run_id}, {"$set": {"status": "completed", "updated_at": now_iso()}})
        await database.tasks.update_one(
            {"audit_run_id": run_id, "task_type": "reporter"},
            {"$set": {"status": "completed", "output": "LLM draft saved to report workspace."}},
        )

    await log_event("analyzed-run", f"Generated {payload.analysis_type} using {payload.provider}:{payload.model}.")
    return await get_run_bundle(run_id)


@app.get("/api/findings")
async def get_findings():
    return [clean_document(item) async for item in database.findings.find({}, {"_id": 0}).sort("created_at", -1)]


@app.get("/api/reports")
async def get_reports():
    return [clean_document(item) async for item in database.reports.find({}, {"_id": 0}).sort("updated_at", -1)]


@app.get("/api/audit-log")
async def get_audit_log():
    return [clean_document(item) async for item in database.audit_logs.find({}, {"_id": 0}).sort("created_at", -1)]