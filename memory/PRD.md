# PRD

## Original Problem Statement
Go on Priority C. User choices: support all currently available providers, optimize for reliability / fallback first, let operators choose routing policy in both Settings and Run Detail, and when the primary fails try one fallback then show the error reason if it also fails.

## User Choices
- Routing scope: all current providers
- Primary optimization: reliability first
- Policy selection surface: Settings + Run Detail
- Fallback behavior: one fallback only, then show why it failed

## Architecture Decisions
- Introduced a config-backed routing layer driven by `/app/configs/routing.yaml` so routing policy behavior is explicit and maintainable
- Kept the first router deliberately simple: primary route + one fallback route, no multi-hop chains yet
- Added a persisted default routing policy in backend storage so Settings can define the app default while Run Detail can override it per analysis
- Preserved direct/manual provider selection as a first-class option so existing workflows remain intact
- Hardened both routing config loading and frontend API base handling so the new layer is resilient without hiding config mistakes

## What’s Implemented
- Added `/app/backend/routing_service.py` with config sync, default routing settings, and safe fallback to built-in policies if `configs/routing.yaml` is missing or malformed
- Added routing policy APIs: list policies and update the default policy
- Extended run analysis so `routing_policy_id` can select a policy, attempt the primary route, try one fallback, and return explicit primary/fallback error reasons if both fail
- Added Settings UI for default routing policy selection and policy cards
- Added Run Detail routing selector with primary/fallback route preview and clear one-fallback note
- Updated README and requirements-gap docs to reflect that Priority C is now partially implemented
- Added regression coverage for routing policy APIs, default updates, fallback error reporting, and direct/manual mode regression; test suites now pass

## Prioritized Backlog
### P0
- Add richer routing telemetry and route health indicators

### P1
- Expand beyond reliability-first into latency/cost-aware strategies
- Add policy editing instead of config-only seeded policies
- Persist route traces per analysis more explicitly in the UI/history

### P2
- Start Priority D multi-agent runtime design
- Later add Priority E execution/scanner plane
- Strengthen auth/RBAC, observability, and production secret lifecycle

## Next Tasks
- Build the next router iteration with latency/cost signals and richer route metadata
- Add policy editing and validation UI
- Begin Priority D: real multi-agent runtime and coordination layer
