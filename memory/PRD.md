# PRD — Unified Agentic Red-Team Audit Platform MVP

## Original problem statement
making a red team tool. see file on what and how to do.

## User choices
- Authorized internal red-team / audit use only
- Follow the PDF blueprint closely
- Single-admin first
- Build all core blueprint sections if possible
- Keep separate sections/buttons so outputs can be isolated, read clearly, and copy/pasted
- Include LLM-assisted analysis using the universal key where possible
- Prefer support for OpenAI, Anthropic, OpenRouter, and MiniMax if possible
- Keep README updated with the build direction

## Architecture decisions
- Chosen stack: React frontend + FastAPI backend + MongoDB, adapted to the available environment
- Blueprint adaptation: replaced the blueprint’s Postgres-first MVP with MongoDB-backed entities because the environment provides MongoDB out of the box
- Safety model: exploratory vs consent-gated modes, fail-closed policy checks, explicit scope records, human-review language in reports
- LLM model plane: OpenAI and Anthropic run through EMERGENT_LLM_KEY; OpenRouter and MiniMax provider slots are available for custom keys/base URLs
- UX model: technical dark control-plane dashboard with separate pages plus isolated evidence/report sections and copy actions

## What’s implemented
### Backend
- FastAPI API for overview, targets, policies, providers, audit runs, run detail, findings, reports, and audit log
- MongoDB persistence for targets, policies, providers, runs, tasks, findings, evidence sections, reports, and logs
- Seed data for immediate exploration
- LLM-assisted report/finding/remediation drafting endpoint
- Run creation with mode validation and consent-token gating for consent_gated mode

### Frontend
- Sidebar dashboard with pages: Overview, Targets, Policies, Audit Runs, Run Detail, Findings, Reports, Settings, Audit Log
- Overview metrics and charts
- Target creation and scoped registry
- Policy editing with deep-mode warning banner
- Audit run creation flow and run list
- Run detail tabs for tasks, findings, evidence, and report
- Save/copy evidence sections with graceful clipboard-denied handling
- Empty-state guidance for runs with no findings yet
- Provider settings cards for OpenAI, Anthropic, OpenRouter, and MiniMax
- Report library with copyable markdown blocks

### Verification completed
- Backend health and data endpoints verified with curl
- Created runs, saved sections, and generated OpenAI draft reports successfully
- Browser flow verified for overview, targets, audit runs, run detail tabs, empty findings state, and clipboard-denied behavior
- Formal QA pass executed via testing agent; critical copy crash fixed afterward

## Prioritized backlog
### P0
- Add encrypted provider-key storage instead of plain persistence for custom provider keys
- Add explicit human-review/export approval workflow instead of status-only review labels
- Add import pipeline for pasted scanner outputs to auto-create normalized findings

### P1
- Add report export formats (markdown file / PDF)
- Add richer task orchestration states and progress visualization
- Add finding creation/edit workflow and remediation tracking statuses
- Add provider-specific validation for OpenRouter and MiniMax custom-key flows

### P2
- Add workspace support beyond single-admin mode
- Add artifact uploads/screenshots instead of text-only evidence sections
- Add observability traces and richer analytics
- Add code/repo passive indexing and additional deterministic technique engines

## Next tasks
1. Secure custom provider credentials with encryption and key rotation UX
2. Add structured findings import from Semgrep/CodeQL/web passive outputs
3. Add export approval flow and downloadable report artifacts
4. Add richer provider compatibility testing for OpenRouter and MiniMax
