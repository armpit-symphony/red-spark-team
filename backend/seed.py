from datetime import datetime, timedelta, timezone
from uuid import uuid4


def seed_timestamp(offset_days: int) -> str:
    return (datetime.now(timezone.utc) - timedelta(days=offset_days)).isoformat()


async def seed_database(db):
    if await db.targets.count_documents({}) > 0:
        return

    target_id = str(uuid4())
    run_id = str(uuid4())
    finding_one_id = str(uuid4())
    finding_two_id = str(uuid4())
    report_id = str(uuid4())

    await db.targets.insert_one(
        {
            "id": target_id,
            "name": "Internal Control Plane",
            "target_type": "webapp",
            "locator": "https://security.internal.example",
            "scope_limit": "Passive checks only on authenticated admin views and public assets.",
            "allowed_modes": ["exploratory", "consent_gated"],
            "notes": "Primary internal surface for validating policy banners, headers, and operator flows.",
            "created_at": seed_timestamp(9),
            "last_audit_at": seed_timestamp(1),
        }
    )

    await db.policies.insert_one(
        {
            "id": "default-policy",
            "passive_rules": [
                "Fail closed when scope is missing or malformed.",
                "Allow exploratory checks only on explicit targets.",
                "Require artifact capture for every promoted finding.",
            ],
            "deep_mode_requirements": [
                "Written consent confirmed.",
                "Runtime consent token entered.",
                "Human review required before report export.",
            ],
            "deep_mode_consent_token": "AUTHORIZED-DEEP",
            "export_requires_review": True,
            "secret_redaction_enabled": True,
            "deny_by_default_egress": True,
            "updated_at": seed_timestamp(0),
        }
    )

    await db.providers.insert_many(
        [
            {
                "provider": "openai",
                "label": "OpenAI",
                "model": "gpt-5.2",
                "enabled": True,
                "auth_mode": "universal",
                "base_url": "",
                "custom_api_key": "",
                "key_last4": "3649",
                "status": "ready",
                "updated_at": seed_timestamp(0),
            },
            {
                "provider": "anthropic",
                "label": "Anthropic",
                "model": "claude-sonnet-4-5-20250929",
                "enabled": True,
                "auth_mode": "universal",
                "base_url": "",
                "custom_api_key": "",
                "key_last4": "3649",
                "status": "ready",
                "updated_at": seed_timestamp(0),
            },
            {
                "provider": "openrouter",
                "label": "OpenRouter",
                "model": "openai/gpt-4.1-mini",
                "enabled": False,
                "auth_mode": "custom",
                "base_url": "https://openrouter.ai/api/v1",
                "custom_api_key": "",
                "key_last4": "",
                "status": "custom-key-required",
                "updated_at": seed_timestamp(0),
            },
            {
                "provider": "minimax",
                "label": "MiniMax",
                "model": "MiniMax-Text-01",
                "enabled": False,
                "auth_mode": "custom",
                "base_url": "https://api.minimax.chat/v1",
                "custom_api_key": "",
                "key_last4": "",
                "status": "custom-key-required",
                "updated_at": seed_timestamp(0),
            },
        ]
    )

    await db.runs.insert_one(
        {
            "id": run_id,
            "target_id": target_id,
            "target_name": "Internal Control Plane",
            "target_locator": "https://security.internal.example",
            "mode": "exploratory",
            "objective": "Review passive posture, scope boundaries, and evidence packaging UX.",
            "scope_notes": "Strictly passive review. No active exploitation or destructive validation.",
            "status": "completed",
            "created_at": seed_timestamp(2),
            "updated_at": seed_timestamp(1),
        }
    )

    await db.tasks.insert_many(
        [
            {
                "id": str(uuid4()),
                "audit_run_id": run_id,
                "title": "Policy gate validation",
                "task_type": "policy_gate",
                "status": "completed",
                "output": "Scope and mode matched policy. Export remains review-gated.",
                "created_at": seed_timestamp(2),
            },
            {
                "id": str(uuid4()),
                "audit_run_id": run_id,
                "title": "Evidence normalization",
                "task_type": "evidence_normalizer",
                "status": "completed",
                "output": "Normalized passive findings into canonical schema and linked raw sections.",
                "created_at": seed_timestamp(2),
            },
            {
                "id": str(uuid4()),
                "audit_run_id": run_id,
                "title": "Draft report assembly",
                "task_type": "reporter",
                "status": "completed",
                "output": "Prepared draft report and remediation stack for admin review.",
                "created_at": seed_timestamp(2),
            },
        ]
    )

    await db.findings.insert_many(
        [
            {
                "id": finding_one_id,
                "audit_run_id": run_id,
                "title": "CSP policy weak on admin shell",
                "severity": "medium",
                "confidence": "high",
                "status": "open",
                "affected_surfaces": ["/admin", "/settings"],
                "evidence": "Observed permissive script-src and missing frame-ancestors control on admin shell.",
                "remediation": "Tighten CSP directives, restrict inline execution, and add frame-ancestors 'none'.",
                "created_at": seed_timestamp(2),
            },
            {
                "id": finding_two_id,
                "audit_run_id": run_id,
                "title": "Deep mode banner missing explicit consent reference",
                "severity": "low",
                "confidence": "medium",
                "status": "review",
                "affected_surfaces": ["/runs/new"],
                "evidence": "Operator flow warned about elevated mode, but the required written consent reference was unclear.",
                "remediation": "Add written-consent checklist, token requirement, and human review checkpoint text.",
                "created_at": seed_timestamp(2),
            },
        ]
    )

    await db.artifacts.insert_many(
        [
            {
                "id": str(uuid4()),
                "audit_run_id": run_id,
                "section_key": "scope-brief",
                "title": "Scope Brief",
                "content": "Target: Internal Control Plane\nMode: Exploratory\nBoundaries: Passive headers, auth flow review, evidence packaging only.",
                "format": "text",
                "created_at": seed_timestamp(2),
                "updated_at": seed_timestamp(1),
            },
            {
                "id": str(uuid4()),
                "audit_run_id": run_id,
                "section_key": "tool-output",
                "title": "Tool Output",
                "content": "semgrep summary:\n- weak CSP on /admin\n- inconsistent anti-framing policy\n\nmanual review:\n- consent banner text needs tightening",
                "format": "text",
                "created_at": seed_timestamp(2),
                "updated_at": seed_timestamp(1),
            },
            {
                "id": str(uuid4()),
                "audit_run_id": run_id,
                "section_key": "evidence-pack",
                "title": "Evidence Pack",
                "content": "Header capture attached. Screenshot references stored. Normalized notes prepared for admin handoff.",
                "format": "markdown",
                "created_at": seed_timestamp(2),
                "updated_at": seed_timestamp(1),
            },
        ]
    )

    await db.reports.insert_one(
        {
            "id": report_id,
            "audit_run_id": run_id,
            "title": "Internal Control Plane Review",
            "executive_summary": "Passive review found policy clarity gaps and one medium-priority header hardening issue.",
            "markdown": "# Internal Control Plane Review\n\n## Scope Alignment\nPassive-only review confirmed.\n\n## Priority Risks\n- Medium: Weak CSP on admin shell\n- Low: Deep mode consent copy needs strengthening\n\n## Remediation Notes\nTighten CSP and reinforce consent copy before enabling deeper workflows.",
            "review_status": "human-review-required",
            "created_at": seed_timestamp(1),
            "updated_at": seed_timestamp(1),
        }
    )

    await db.audit_logs.insert_many(
        [
            {
                "id": str(uuid4()),
                "actor": "single-admin",
                "action": "seeded-platform",
                "details": "Created baseline target, run, findings, providers, and report.",
                "created_at": seed_timestamp(9),
            },
            {
                "id": str(uuid4()),
                "actor": "single-admin",
                "action": "completed-run",
                "details": "Closed exploratory run for Internal Control Plane and prepared report draft.",
                "created_at": seed_timestamp(1),
            },
        ]
    )
