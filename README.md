# Red Spark Team

Authorized internal red-team audit platform focused on governed workflows, evidence packaging, and LLM-assisted report drafting.

## Product direction

- Single-admin control plane for authorized internal audits only
- Strict scope-first workflow with exploratory and consent-gated modes
- Separate sections for reading, copying, and pasting evidence and report outputs
- LLM-assisted analysis wired for OpenAI/Anthropic via universal key, with provider slots for OpenRouter and MiniMax

## Current architecture

- **Frontend:** React dashboard with a persistent control-plane sidebar and separate pages for overview, targets, policies, runs, findings, reports, settings, and audit log
- **Backend:** FastAPI API with MongoDB-backed storage for targets, policies, runs, findings, sections, reports, and audit events
- **Data flow:** create target -> launch run -> save isolated sections -> generate LLM output -> review findings/report

## UX decisions

- High-contrast technical dark UI following the blueprint closely
- Evidence and report blocks are intentionally isolated for copy/paste workflows
- Deep mode is visually separated and token-gated to reinforce safe operator behavior

## In progress

- Backend API and seeded sample data are in place
- Frontend routes and workflows are built
- Next focus is service startup verification, UI validation, and end-to-end testing
