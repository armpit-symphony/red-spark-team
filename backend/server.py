from collections import Counter
import json
import re
from typing import Any
from uuid import uuid4

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from database import clean_document, database
from llm_service import run_provider_analysis
from model_catalog_service import refresh_openrouter_catalog
from models import AnalysisRequest, ModelCatalogRefreshRequest, PolicyUpdate, ProviderUpdate, RunCreate, ScannerImportRequest, SectionUpsert, TargetCreate, now_iso
from security_utils import encrypt_secret
from seed import seed_database


app = FastAPI(title="Unified Agentic Red-Team Audit Platform")

SEVERITY_MAP = {
    "critical": "critical",
    "high": "high",
    "medium": "medium",
    "moderate": "medium",
    "warning": "medium",
    "low": "low",
    "info": "low",
    "informational": "low",
}
CONFIDENCE_MAP = {
    "high": "high",
    "medium": "medium",
    "med": "medium",
    "low": "low",
}
JSON_FINDING_KEYS = ["findings", "results", "issues", "vulnerabilities", "alerts", "items", "data", "matches"]

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


def provider_has_custom_key(provider: dict[str, Any]) -> bool:
    return bool(provider.get("encrypted_custom_api_key") or provider.get("custom_api_key"))


def derive_provider_status(enabled: bool, auth_mode: str, has_custom_key: bool) -> str:
    if not enabled:
        return "disabled"
    if auth_mode == "custom" and not has_custom_key:
        return "custom-key-required"
    return "ready"


def serialize_provider(provider: dict[str, Any] | None) -> dict[str, Any] | None:
    record = clean_document(provider)
    if not record:
        return None

    has_custom_key = provider_has_custom_key(record)
    response = {key: value for key, value in record.items() if key not in {"custom_api_key", "encrypted_custom_api_key"}}
    response["has_custom_key"] = has_custom_key
    response["key_last4"] = response.get("key_last4", "") if has_custom_key else ""
    response["status"] = derive_provider_status(response.get("enabled", False), response.get("auth_mode", "universal"), has_custom_key)
    return response


def normalize_review_status(value: str | None) -> str:
    if value == "approved":
        return "approved"
    return "pending_review"


def serialize_report(report: dict[str, Any] | None) -> dict[str, Any] | None:
    record = clean_document(report)
    if not record:
        return None

    record["review_status"] = normalize_review_status(record.get("review_status"))
    record["can_export"] = record["review_status"] == "approved"
    return record


def normalize_severity(value: str | None) -> str | None:
    if not value:
        return None

    cleaned = re.sub(r"[^a-zA-Z]+", " ", value).strip().lower()
    if not cleaned:
        return None

    direct = SEVERITY_MAP.get(cleaned.replace(" ", "_"))
    if direct:
        return direct

    for token in cleaned.split():
        severity = SEVERITY_MAP.get(token)
        if severity:
            return severity

    return None


def normalize_confidence(value: str | None) -> str:
    if not value:
        return "medium"

    cleaned = re.sub(r"[^a-zA-Z]+", " ", value).strip().lower()
    if not cleaned:
        return "medium"

    for token in cleaned.split():
        normalized = CONFIDENCE_MAP.get(token)
        if normalized:
            return normalized

    return "medium"


def first_non_empty(*values: Any) -> str:
    for value in values:
        if isinstance(value, str) and value.strip():
            return value.strip()
    return ""


def normalize_surfaces(value: Any) -> list[str]:
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    if isinstance(value, str) and value.strip():
        return [value.strip()]
    return []


def make_finding_document(
    run_id: str,
    source_name: str,
    import_format: str,
    title: str,
    severity: str,
    evidence: str,
    remediation: str,
    confidence: str,
    affected_surfaces: list[str],
) -> dict[str, Any]:
    return {
        "id": str(uuid4()),
        "audit_run_id": run_id,
        "title": title,
        "severity": severity,
        "confidence": confidence,
        "status": "pending_review",
        "affected_surfaces": affected_surfaces,
        "evidence": evidence,
        "remediation": remediation,
        "source_name": source_name,
        "import_format": import_format,
        "created_at": now_iso(),
    }


def extract_json_candidates(payload: Any) -> list[dict[str, Any]]:
    if isinstance(payload, list):
        return [item for item in payload if isinstance(item, dict)]

    if isinstance(payload, dict):
        for key in JSON_FINDING_KEYS:
            value = payload.get(key)
            if isinstance(value, list):
                return [item for item in value if isinstance(item, dict)]
        return [payload]

    return []


def normalize_json_candidate(item: dict[str, Any], run_id: str, source_name: str) -> tuple[dict[str, Any] | None, str | None]:
    title = first_non_empty(
        item.get("title"),
        item.get("name"),
        item.get("check_name"),
        item.get("check_title"),
        item.get("rule"),
        item.get("issue"),
        item.get("vulnerability"),
        item.get("finding"),
    )
    severity = normalize_severity(
        first_non_empty(item.get("severity"), item.get("risk"), item.get("priority"), item.get("level"), item.get("impact"))
    )

    if not title or not severity:
        return None, "Missing title or severity"

    evidence = first_non_empty(
        item.get("evidence"),
        item.get("description"),
        item.get("details"),
        item.get("message"),
        item.get("summary"),
        item.get("output"),
        json.dumps(item, ensure_ascii=False),
    )
    remediation = first_non_empty(
        item.get("remediation"),
        item.get("recommendation"),
        item.get("fix"),
        item.get("solution"),
        "Review raw scanner context and confirm the right remediation before closure.",
    )
    confidence = normalize_confidence(first_non_empty(item.get("confidence"), item.get("likelihood"), item.get("precision")))
    affected_surfaces = normalize_surfaces(
        item.get("affected_surfaces") or item.get("paths") or item.get("locations") or item.get("path") or item.get("url") or item.get("file")
    )

    return make_finding_document(run_id, source_name, "json", title, severity, evidence, remediation, confidence, affected_surfaces), None


def split_text_candidates(raw_text: str) -> list[str]:
    blocks = [block.strip() for block in re.split(r"\n\s*\n+", raw_text.strip()) if block.strip()]
    if len(blocks) != 1:
        return blocks

    bullet_lines = [line.strip() for line in raw_text.splitlines() if line.strip()]
    structured_lines = [line for line in bullet_lines if line.lstrip().startswith(("-", "*"))]
    return structured_lines if len(structured_lines) >= 2 else blocks


def clean_title_line(line: str) -> str:
    cleaned = line.strip().lstrip("#*-0123456789. ").strip()
    cleaned = re.sub(r"^title\s*:\s*", "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"^finding\s*:\s*", "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(
        r"^\[?(critical|high|medium|moderate|warning|low|info|informational)\]?\s*[:\-–]\s*",
        "",
        cleaned,
        flags=re.IGNORECASE,
    )
    return cleaned.strip()


def normalize_text_candidate(block: str, run_id: str, source_name: str) -> tuple[dict[str, Any] | None, str | None]:
    lines = [line.strip() for line in block.splitlines() if line.strip()]
    if not lines:
        return None, "Empty block"

    severity = None
    title = ""
    evidence_parts: list[str] = []
    remediation_parts: list[str] = []
    confidence_value = ""
    affected_surfaces: list[str] = []

    for line in lines:
        lower = line.lower()
        severity = severity or normalize_severity(line)

        if lower.startswith(("severity:", "risk:", "priority:", "level:")):
            continue

        if lower.startswith(("title:", "finding:")):
            title = clean_title_line(line)
            continue

        if lower.startswith(("remediation:", "recommendation:", "fix:", "solution:")):
            remediation_parts.append(line.split(":", 1)[1].strip())
            continue

        if lower.startswith(("evidence:", "description:", "details:", "proof:", "observation:")):
            evidence_parts.append(line.split(":", 1)[1].strip())
            continue

        if lower.startswith(("confidence:",)):
            confidence_value = line.split(":", 1)[1].strip()
            continue

        if lower.startswith(("path:", "url:", "file:", "surface:")):
            affected_surfaces.append(line.split(":", 1)[1].strip())
            continue

        if not title:
            title = clean_title_line(line)
            continue

        evidence_parts.append(line)

    if not title or not severity:
        return None, "Missing title or severity"

    evidence = "\n".join(part for part in evidence_parts if part).strip() or block.strip()
    remediation = "\n".join(part for part in remediation_parts if part).strip() or "Review raw scanner context and confirm the right remediation before closure."
    confidence = normalize_confidence(confidence_value)
    surfaces = [surface for surface in affected_surfaces if surface]

    return make_finding_document(run_id, source_name, "text", title, severity, evidence, remediation, confidence, surfaces), None


def build_import_excerpt(content: str, source_name: str, import_format: str) -> str:
    trimmed = content.strip()
    if len(trimmed) > 12000:
        trimmed = f"{trimmed[:12000]}\n\n[truncated after 12000 characters]"

    return f"## Imported from {source_name} ({import_format.upper()})\n\n{trimmed}"


def report_filename(title: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", title.lower()).strip("-") or "report"
    return f"{slug}.md"


async def migrate_provider_storage():
    async for provider in database.providers.find({}, {"_id": 0}):
        record = clean_document(provider) or {}
        legacy_key = (record.get("custom_api_key") or "").strip()
        encrypted_key = (record.get("encrypted_custom_api_key") or "").strip()
        has_custom_key = bool(legacy_key or encrypted_key)
        expected_status = derive_provider_status(record.get("enabled", False), record.get("auth_mode", "universal"), has_custom_key)
        update_data: dict[str, Any] = {}

        if legacy_key and not encrypted_key:
            update_data["encrypted_custom_api_key"] = encrypt_secret(legacy_key)
            update_data["custom_api_key"] = ""
            update_data["key_last4"] = legacy_key[-4:]
            has_custom_key = True
            expected_status = derive_provider_status(record.get("enabled", False), record.get("auth_mode", "universal"), has_custom_key)

        if record.get("status") != expected_status:
            update_data["status"] = expected_status

        if update_data:
            await database.providers.update_one({"provider": record["provider"]}, {"$set": update_data})


async def migrate_report_reviews():
    await database.reports.update_many(
        {"review_status": {"$in": ["human-review-required", None]}},
        {"$set": {"review_status": "pending_review"}},
    )
    await database.reports.update_many(
        {"review_status": {"$exists": False}},
        {"$set": {"review_status": "pending_review"}},
    )


async def get_run_bundle(run_id: str):
    run_record = clean_document(await database.runs.find_one({"id": run_id}, {"_id": 0}))
    if not run_record:
        raise HTTPException(status_code=404, detail="Run not found.")

    tasks = [clean_document(item) async for item in database.tasks.find({"audit_run_id": run_id}, {"_id": 0})]
    findings = [clean_document(item) async for item in database.findings.find({"audit_run_id": run_id}, {"_id": 0})]
    sections = [clean_document(item) async for item in database.artifacts.find({"audit_run_id": run_id}, {"_id": 0})]
    report = serialize_report(await database.reports.find_one({"audit_run_id": run_id}, {"_id": 0}))
    return {"run": run_record, "tasks": tasks, "findings": findings, "sections": sections, "report": report}


@app.on_event("startup")
async def startup_event():
    await seed_database(database)
    await migrate_provider_storage()
    await migrate_report_reviews()
    await refresh_openrouter_catalog(database)


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
    async for item in database.providers.find({}, {"_id": 0}).sort("label", 1):
        providers.append(serialize_provider(item))
    return providers


@app.get("/api/model-catalog")
async def get_model_catalog(provider: str):
    if provider != "openrouter":
        return {"provider": provider, "models": [], "model_count": 0, "source": "unsupported", "refresh_status": "unsupported"}

    meta = clean_document(await database.model_catalog_meta.find_one({"provider": provider}, {"_id": 0})) or {
        "provider": provider,
        "model_count": 0,
        "source": "unknown",
        "refresh_status": "unknown",
        "last_refreshed_at": "",
        "last_error": "",
    }
    models = [clean_document(item) async for item in database.model_catalog.find({"provider": provider}, {"_id": 0}).sort("name", 1)]
    return {**meta, "models": models}


@app.post("/api/model-catalog/refresh")
async def refresh_model_catalog(payload: ModelCatalogRefreshRequest):
    if payload.provider != "openrouter":
        raise HTTPException(status_code=400, detail="Only the openrouter catalog is supported right now.")

    meta = await refresh_openrouter_catalog(database)
    await log_event("refreshed-model-catalog", f"Refreshed {payload.provider} model catalog with {meta['model_count']} entries via {meta['source']}.")
    models = [clean_document(item) async for item in database.model_catalog.find({"provider": payload.provider}, {"_id": 0}).sort("name", 1)]
    return {**meta, "models": models}


@app.put("/api/providers/{provider_name}")
async def update_provider(provider_name: str, payload: ProviderUpdate):
    existing = clean_document(await database.providers.find_one({"provider": provider_name}, {"_id": 0}))
    if not existing:
        raise HTTPException(status_code=404, detail="Provider not found.")

    custom_api_key = payload.custom_api_key.strip()
    has_custom_key = bool(custom_api_key or existing.get("encrypted_custom_api_key") or existing.get("custom_api_key"))
    status = derive_provider_status(payload.enabled, payload.auth_mode, has_custom_key)

    update_data = {
        "model": payload.model,
        "enabled": payload.enabled,
        "auth_mode": payload.auth_mode,
        "base_url": payload.base_url.strip(),
        "status": status,
        "updated_at": now_iso(),
    }
    if custom_api_key:
        update_data["encrypted_custom_api_key"] = encrypt_secret(custom_api_key)
        update_data["custom_api_key"] = ""
        update_data["key_last4"] = custom_api_key[-4:]

    await database.providers.update_one({"provider": provider_name}, {"$set": update_data})
    await log_event("updated-provider", f"Updated {provider_name} provider settings.")
    response = serialize_provider(await database.providers.find_one({"provider": provider_name}, {"_id": 0}))
    return response


@app.delete("/api/providers/{provider_name}/custom-key")
async def delete_provider_custom_key(provider_name: str):
    existing = clean_document(await database.providers.find_one({"provider": provider_name}, {"_id": 0}))
    if not existing:
        raise HTTPException(status_code=404, detail="Provider not found.")

    status = derive_provider_status(existing.get("enabled", False), existing.get("auth_mode", "universal"), False)
    await database.providers.update_one(
        {"provider": provider_name},
        {
            "$set": {"status": status, "updated_at": now_iso(), "key_last4": ""},
            "$unset": {"encrypted_custom_api_key": "", "custom_api_key": ""},
        },
    )
    await log_event("deleted-provider-key", f"Removed stored custom key for {provider_name}.")
    return serialize_provider(await database.providers.find_one({"provider": provider_name}, {"_id": 0}))


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
                    "review_status": "pending_review",
                    "created_at": now_iso(),
                    "updated_at": now_iso(),
                },
                "$unset": {"approved_at": ""},
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


@app.post("/api/runs/{run_id}/scanner-import")
async def import_scanner_output(run_id: str, payload: ScannerImportRequest):
    run_record = clean_document(await database.runs.find_one({"id": run_id}, {"_id": 0}))
    if not run_record:
        raise HTTPException(status_code=404, detail="Run not found.")

    content = payload.content.strip()
    if not content:
        raise HTTPException(status_code=400, detail="Scanner content cannot be empty.")

    normalized_findings: list[dict[str, Any]] = []
    skipped_items: list[str] = []
    detected_count = 0

    if payload.import_format == "json":
        try:
            parsed = json.loads(content)
        except json.JSONDecodeError as exc:
            raise HTTPException(status_code=400, detail=f"Invalid JSON payload: {exc.msg}.") from exc

        candidates = extract_json_candidates(parsed)
        detected_count = len(candidates)
        for index, item in enumerate(candidates, start=1):
            finding, reason = normalize_json_candidate(item, run_id, payload.source_name)
            if finding:
                normalized_findings.append(finding)
            else:
                skipped_items.append(f"Item {index}: {reason}")
    else:
        candidates = split_text_candidates(content)
        detected_count = len(candidates)
        for index, block in enumerate(candidates, start=1):
            finding, reason = normalize_text_candidate(block, run_id, payload.source_name)
            if finding:
                normalized_findings.append(finding)
            else:
                skipped_items.append(f"Block {index}: {reason}")

    if not normalized_findings:
        raise HTTPException(status_code=400, detail="No valid findings were detected. Each item needs at least a title and severity.")

    await database.findings.insert_many(normalized_findings)

    artifact = clean_document(await database.artifacts.find_one({"audit_run_id": run_id, "section_key": "tool-output"}, {"_id": 0})) or {}
    existing_content = artifact.get("content", "").strip()
    appended_excerpt = build_import_excerpt(content, payload.source_name, payload.import_format)
    merged_content = appended_excerpt if not existing_content else f"{existing_content}\n\n---\n\n{appended_excerpt}"

    await database.artifacts.update_one(
        {"audit_run_id": run_id, "section_key": "tool-output"},
        {
            "$set": {
                "id": artifact.get("id", str(uuid4())),
                "audit_run_id": run_id,
                "section_key": "tool-output",
                "title": artifact.get("title", "Tool Output"),
                "content": merged_content,
                "format": artifact.get("format", "text"),
                "created_at": artifact.get("created_at", now_iso()),
                "updated_at": now_iso(),
            }
        },
        upsert=True,
    )

    summary = (
        f"Imported {len(normalized_findings)} normalized finding(s) from {payload.source_name} "
        f"using {payload.import_format.upper()} input. Skipped {len(skipped_items)} item(s)."
    )
    await database.tasks.update_one(
        {"audit_run_id": run_id, "task_type": "evidence_normalizer"},
        {"$set": {"status": "completed", "output": summary}},
    )
    await database.runs.update_one({"id": run_id}, {"$set": {"updated_at": now_iso()}})
    await log_event("imported-scanner-output", summary)

    return {
        "bundle": await get_run_bundle(run_id),
        "summary": {
            "imported_count": len(normalized_findings),
            "skipped_count": len(skipped_items),
            "detected_count": detected_count,
            "source_name": payload.source_name,
            "import_format": payload.import_format,
            "skipped_items": skipped_items[:5],
        },
    }


@app.get("/api/reports")
async def get_reports():
    reports = [serialize_report(item) async for item in database.reports.find({}, {"_id": 0}).sort("updated_at", -1)]
    return [report for report in reports if report]


@app.post("/api/reports/{report_id}/approve")
async def approve_report(report_id: str):
    report = clean_document(await database.reports.find_one({"id": report_id}, {"_id": 0}))
    if not report:
        raise HTTPException(status_code=404, detail="Report not found.")

    if normalize_review_status(report.get("review_status")) != "approved":
        await database.reports.update_one(
            {"id": report_id},
            {"$set": {"review_status": "approved", "approved_at": now_iso(), "updated_at": now_iso()}},
        )
        await log_event("approved-report", f"Approved report {report['title']} for export.")

    return serialize_report(await database.reports.find_one({"id": report_id}, {"_id": 0}))


@app.get("/api/reports/{report_id}/export")
async def export_report(report_id: str):
    report = serialize_report(await database.reports.find_one({"id": report_id}, {"_id": 0}))
    if not report:
        raise HTTPException(status_code=404, detail="Report not found.")
    if not report.get("can_export"):
        raise HTTPException(status_code=400, detail="Report must be approved before export.")

    await log_event("exported-report", f"Exported report {report['title']}.")
    return {"filename": report_filename(report["title"]), "markdown": report.get("markdown", "")}


@app.get("/api/audit-log")
async def get_audit_log():
    return [clean_document(item) async for item in database.audit_logs.find({}, {"_id": 0}).sort("created_at", -1)]