# PRD

## Original Problem Statement
Proceed with Priority B after the gap analysis: build OpenRouter setup + model catalog direction with these choices — OpenRouter Models API + manual fallback list, refresh on startup + manual refresh, UI in both Settings and Run Detail, and model name display first.

## User Choices
- Catalog source: OpenRouter Models API + manual fallback list
- Refresh strategy: backend startup refresh + manual refresh
- UI scope: both Settings and Run Detail
- Operator-visible fields: model name only

## Architecture Decisions
- Added a dedicated backend model catalog service for OpenRouter so startup sync, manual refresh, and fallback handling stay isolated from general API logic
- Stored normalized catalog metadata in MongoDB for fast UI reads and refresh-state visibility
- Kept the first UI pass intentionally simple: model-name browsing only, with richer metadata stored for later use
- Preserved OpenRouter as an opt-in provider for Run Detail by showing the picker when OpenRouter is enabled
- Hardened frontend API base handling so full-domain env values without `/api` are normalized safely in the browser

## What’s Implemented
- Added `/app/backend/model_catalog_service.py` to fetch and normalize OpenRouter models, with a curated fallback list if the remote API is unavailable
- Added startup refresh + manual refresh endpoints for the OpenRouter catalog
- Added Settings page catalog controls and OpenRouter model browsing, including a manual refresh button
- Added Run Detail model picker for OpenRouter using the catalog data
- Added docs updates in `README.md`, `docs/openrouter-setup.md`, and `docs/requirements-gap-analysis.md`
- Added regression coverage for Priority B and kept existing provider/import/report workflows passing
- Fixed frontend API URL normalization so full-domain `REACT_APP_BACKEND_URL` values correctly target `/api`

## Prioritized Backlog
### P0
- Expand from OpenRouter-only catalog to a broader cross-provider model registry

### P1
- Add richer browsing/filtering (pricing, context window, descriptions) when operators need it
- Start Priority C with routing groups, fallback policy objects, and route decision logging

### P2
- Add multi-agent runtime design and built-in execution/scanner infrastructure
- Strengthen production auth/RBAC, secrets lifecycle, and observability

## Next Tasks
- Begin Priority C: multi-model routing and fallback policy layer
- Add provider health / stale-catalog indicators and richer catalog filters
- Extend model registry support beyond OpenRouter
