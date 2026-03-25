# PRD

## Original Problem Statement
Use the supplied requirements gap analysis in the project, add roadmap/gap documentation, and start building the missing pieces with this priority order: A) OpenAI + Anthropic custom key support minimum, B) OpenRouter setup / catalog direction, C) routing, D) multi-agent runtime, E) built-in audit execution.

## User Direction
- Do both: document the gap analysis and begin implementation work
- Priority A first: OpenAI and Anthropic custom key support minimum
- Priority B next: OpenRouter setup guidance and model-catalog direction
- Then C, D, E in order

## Architecture Decisions
- Treated Priority A as a verification + documentation hardening task because the runtime already supports encrypted custom key resolution for OpenAI and Anthropic
- Added explicit docs that separate current capability from future roadmap so the repo stays accurate
- Strengthened regression coverage across OpenAI, Anthropic, and OpenRouter custom-key save/remove flows
- Added OpenRouter setup notes based on current docs while clearly marking future catalog/routing work as not yet wired in runtime

## What’s Implemented
- Added `/app/docs/requirements-gap-analysis.md` with implemented / partial / missing status tracking and a priority-based roadmap
- Added `/app/docs/openrouter-setup.md` with current setup guidance, limitations, and next steps
- Updated `README.md` to reflect OpenAI / Anthropic custom-key support and link to the new docs
- Updated the Settings page copy so users understand OpenAI and Anthropic support universal or encrypted custom keys
- Expanded backend regression coverage so provider key encryption/save/remove is tested for OpenAI, Anthropic, and OpenRouter
- Verified the updated provider workflow suite passes: `6 passed`

## Prioritized Backlog
### P0
- Priority B: add OpenRouter model catalog ingestion design and UI plan

### P1
- Priority C: implement routing groups, fallback policy objects, and route decision logging
- Priority D: design real agent runtime state/memory/tool execution layer

### P2
- Priority E: add sandboxed scanner execution and ingestion pipelines
- Add stronger production auth/RBAC, secrets lifecycle, and observability

## Next Tasks
- Start OpenRouter model catalog support and provider model discovery UI
- Define routing schema and fallback behavior for multi-model orchestration
- Add a dedicated implementation roadmap doc for C/D/E architecture work
