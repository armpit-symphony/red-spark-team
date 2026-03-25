# PRD

## Original Problem Statement
Continue the Priority C next action items: add richer routing telemetry, latency/cost-aware strategies, and editable policy management. User choices: score latency + cost + fallback success, show telemetry in Run Detail only, allow policy name/goal/primary/fallback editing, and use the last 25 routed analyses as the scoring memory window.

## User Choices
- Strategy inputs: latency + cost + fallback success
- Telemetry surface: Run Detail only
- Policy editing scope: name, strategy goal, primary route, fallback route
- Memory window: last 25 routed analyses

## Architecture Decisions
- Kept telemetry and scoring in the backend so route ranking logic stays consistent across UI surfaces and future automation
- Stored routing traces per attempt so preferred/backup scoring can use real success and latency history over the configured 25-attempt window
- Limited the first editable policy release to the fields the user requested while keeping direct/manual mode intact
- Kept telemetry display in Run Detail only to avoid cluttering Settings with operational noise
- Added server-side validation to reject identical primary/fallback pairs, preserving the one-fallback resilience intent

## What’s Implemented
- Added routing telemetry summaries and recent trace history based on the last 25 routed analyses
- Added latency/cost/fallback-success-aware route scoring that ranks the preferred and backup route for each policy
- Added editable policy management in Settings for policy name, strategy goal, primary route, and fallback route
- Added Run Detail telemetry cards and recent trace items for the selected routing policy
- Added backend APIs for routing telemetry and policy editing
- Added validation that rejects identical primary/fallback provider-model pairs with HTTP 400
- Expanded regression coverage; the updated Priority C suites now pass after the validation fix

## Prioritized Backlog
### P0
- Add richer telemetry visualizations, route health trend indicators, and clearer scoring explanations

### P1
- Add threshold/weight editing and stronger policy validation rules
- Add deterministic success-path fallback testing for `used_fallback=true`
- Expand strategy types and model/provider-aware route heuristics

### P2
- Start Priority D multi-agent runtime work
- Add deeper observability, auth/RBAC, and long-term route history views
- Broaden provider/model intelligence beyond current manual hints

## Next Tasks
- Add route trend charts and clearer score breakdowns in Run Detail
- Add policy weights/thresholds and stricter editor validation
- Begin Priority D: real multi-agent runtime and coordination flows
