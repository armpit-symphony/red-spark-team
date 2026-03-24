# PRD

## Original Problem Statement
1. Next Priority — build all 3 below

a) Encrypted custom provider key storage
b) Scanner output import into normalized findings
c) Human-review + export approval workflow

2. Scanner Import Scope — Which formats should I support first if I do import next?

Both text and JSON

Copyable markdown only
Downloadable markdown file

## User Choices
- Export format: both copyable and downloadable markdown
- Approval workflow: pending -> approved
- Encrypted provider keys: store encrypted keys and allow update/delete
- Import normalization: skip invalid items when required fields are missing

## Architecture Decisions
- Provider custom keys are encrypted at rest in MongoDB using Fernet before storage and never returned in API responses
- Existing provider settings API was extended to support encrypted save/update and explicit key deletion
- Scanner import was added at the run level so imported findings stay tied to a specific audit run and evidence context
- Text and JSON imports use deterministic normalization rules with invalid entries skipped instead of blocking the full import
- Report approval/export is enforced through backend-gated export endpoints so markdown copy/download only unlocks after approval
- Frontend keeps draft preview visible while gating copy/download actions behind approval status

## What’s Implemented
- Encrypted provider key storage with save/update/delete support and provider readiness status updates
- Startup migration for legacy plaintext provider keys and legacy report review statuses
- Run-level scanner import endpoint for text and JSON input into normalized findings
- Import summary with detected/imported/skipped counts and raw import excerpt appended into tool output evidence
- Human review workflow for reports with pending_review -> approved transition
- Approved report export endpoint returning markdown + filename for copy/download flows
- Settings page updates for secure key messaging and key removal actions
- Run Detail page import panel, import results, finding source badges, and report approval/export controls
- Reports page approval controls and approved markdown copy/download actions
- Regression coverage for provider storage, scanner import, and report approval/export workflows

## Prioritized Backlog
### P0
- Replace derived encryption key material with a dedicated secret env var for stronger key rotation and compartmentalization

### P1
- Add duplicate detection / merge strategy for repeated scanner imports
- Support richer scanner JSON shapes and nested result structures
- Add reviewer identity / approval notes metadata to report approvals

### P2
- Add CSV/SARIF import support
- Add finding-level review states and bulk approval actions
- Add export history timeline and reviewer audit filters

## Next Tasks
- Introduce dedicated encryption secret configuration and rotation path
- Add duplicate import safeguards and clearer import conflict messaging
- Expand report review metadata with approver notes and timestamps in the UI
