from typing import Any


AGENT_ORDER = [
    {"key": "planner", "label": "Planner", "depends_on": [], "section_key": "agent-plan"},
    {"key": "evidence_normalizer", "label": "Evidence Normalizer", "depends_on": ["planner"], "section_key": "normalized-evidence"},
    {"key": "risk_reviewer", "label": "Risk Reviewer", "depends_on": ["planner"], "section_key": "risk-review"},
    {"key": "reporter", "label": "Reporter", "depends_on": ["evidence_normalizer", "risk_reviewer"], "section_key": "report-draft"},
]


def _sections_text(bundle: dict[str, Any]) -> str:
    return "\n\n".join(
        f"[{section.get('title', 'Section')}]\n{section.get('content', '').strip()}"
        for section in bundle.get("sections", [])
        if section.get("content")
    ) or "No section content yet."


def _findings_text(bundle: dict[str, Any]) -> str:
    findings = bundle.get("findings", [])
    if not findings:
        return "No normalized findings yet."
    return "\n".join(
        f"- {finding.get('severity', 'unknown').upper()} | {finding.get('title', 'Untitled')} | {finding.get('evidence', '')[:220]}"
        for finding in findings
    )


def current_run_memory(bundle: dict[str, Any]) -> str:
    run = bundle.get("run", {})
    return (
        f"Run objective: {run.get('objective', '')}\n"
        f"Run mode: {run.get('mode', '')}\n"
        f"Target: {run.get('target_name', '')} ({run.get('target_locator', '')})\n"
        f"Current sections:\n{_sections_text(bundle)}\n\n"
        f"Current findings:\n{_findings_text(bundle)}"
    )


def handoff_summary(agent_key: str) -> str:
    summaries = {
        "planner": "Plan handed off to Evidence Normalizer and Risk Reviewer.",
        "evidence_normalizer": "Normalized evidence handed off to Risk Reviewer and Reporter.",
        "risk_reviewer": "Risk review handed off to Reporter.",
        "reporter": "Report draft handed back to the run workspace.",
    }
    return summaries.get(agent_key, "Agent output handed to the next stage.")


def build_agent_prompt(agent_key: str, bundle: dict[str, Any], outputs: dict[str, str], focus: str) -> str:
    focus_text = focus or "No extra focus provided. Stay defensive, concise, and governance-focused."
    base_context = current_run_memory(bundle)
    prior_outputs = "\n\n".join(
        f"[{key.replace('_', ' ').title()} Output]\n{value.strip()}"
        for key, value in outputs.items()
        if value.strip()
    ) or "No prior agent outputs yet."

    prompts = {
        "planner": (
            "You are the Planner agent in an authorized internal audit workflow. "
            "Create a markdown execution plan with headings: Scope Alignment, Evidence Needed, Review Sequence, Blocking Unknowns, Next Actions."
        ),
        "evidence_normalizer": (
            "You are the Evidence Normalizer agent. Convert the current run evidence into a clean markdown summary with headings: "
            "Normalized Evidence, Confidence Notes, Missing Evidence, Operator Follow-up."
        ),
        "risk_reviewer": (
            "You are the Risk Reviewer agent. Review the normalized evidence and findings and produce markdown with headings: "
            "Top Risks, Severity Review, Exposure Notes, Remediation Priorities."
        ),
        "reporter": (
            "You are the Reporter agent. Produce the final markdown report draft using the prior agent outputs. "
            "Use headings: Executive Summary, Scope Alignment, Priority Risks, Evidence Confidence, Recommended Next Steps, Remediation Notes."
        ),
    }

    return (
        "You are part of a governed internal multi-agent audit runtime. "
        "Do not provide attack steps, payloads, or abuse instructions. Stay defensive and review-focused.\n\n"
        f"Agent role: {agent_key}\n"
        f"Focus: {focus_text}\n\n"
        f"Current run memory:\n{base_context}\n\n"
        f"Prior agent outputs:\n{prior_outputs}\n\n"
        f"Task instructions:\n{prompts[agent_key]}"
    )