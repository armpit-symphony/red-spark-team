# PRD

## Original Problem Statement
Priority D. User choices: agents = Planner + Evidence Normalizer + Risk Reviewer + Reporter, execution = parallel where possible with handoff tracking, memory scope = current run only, and control surface = Run Detail only.

## User Choices
- Agents: Planner, Evidence Normalizer, Risk Reviewer, Reporter
- Execution style: planner first, then parallel middle stage where possible, with tracked handoffs
- Memory scope: current run only
- Control surface: Run Detail only

## Architecture Decisions
- Added a real run-scoped multi-agent runtime with persisted workflow and step records instead of relying on static timeline tasks only
- Kept orchestration in the backend so sequencing, parallel stages, handoffs, and route traces stay authoritative
- Reused the existing routing layer so agent steps can run through direct or policy-based model selection
- Stored agent outputs back into workspace artifacts (`agent-plan`, `normalized-evidence`, `risk-review`, `report-draft`) so they remain part of the run context
- Limited memory to the current run exactly as requested

## What’s Implemented
- Added a new multi-agent runtime with Planner -> parallel Evidence Normalizer + Risk Reviewer -> Reporter
- Added `GET/POST /api/runs/{run_id}/agent-workflow` for latest workflow state and execution
- Added persisted workflow steps with status, route trace, output, error, dependencies, and handoff summary
- Added an Agents tab in Run Detail with workflow launch controls, status cards, and step outputs
- Reporter output now updates the report workspace and report record after workflow completion
- Updated README and gap-analysis docs to reflect that Priority D is now partially implemented
- Self-test passed once with all four agents completing on a live run

## Current Blocking Validation Issue
- Subsequent end-to-end validation is currently blocked by upstream LLM budget exhaustion (`Budget has been exceeded`) for live agent-workflow execution
- Non-LLM regressions and UI surfaces passed; the blocked flow is live POST `/api/runs/{run_id}/agent-workflow` execution while provider budget/quota is exhausted

## Prioritized Backlog
### P0
- Restore valid provider budget/key and re-run live multi-agent workflow validation end-to-end

### P1
- Add retries / resumability for failed steps
- Surface previous successful workflow history when the latest run fails
- Add clearer handoff wording and richer workflow history

### P2
- Start Priority E execution/scanner plane
- Add deeper observability, auth/RBAC, and longer-lived memory options
- Add deterministic fallback-success validation once provider budget is available

## Next Tasks
- Restore LLM budget/key and re-run live Priority D workflow tests
- Add step retry/resume controls and prior-workflow history in the Agents tab
- Begin Priority E: built-in audit execution and scanner integration
