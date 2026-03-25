# Requirements Gap Analysis

This file tracks the current platform against the broader original vision and separates what is already delivered from what is still roadmap work.

## Status key

- **Implemented**
- **Partially implemented (gaps)**
- **Not implemented**

## Current assessment

| Requirement | Status | Current evidence | Key gaps / notes |
|---|---|---|---|
| Accepts user-supplied API keys: OpenAI | Implemented | OpenAI provider supports `auth_mode` + encrypted custom key storage in Settings and backend provider update flows; runtime analysis resolves stored custom key before falling back to the universal key | Current app is still single-admin, not per-user / tenant scoped |
| Accepts user-supplied API keys: Anthropic | Implemented | Anthropic follows the same provider settings and encrypted storage flow as OpenAI | Same single-admin limitation applies |
| Accepts user-supplied API keys: Agentic | Not implemented | No Agentic provider exists in provider seeds, settings UI, runtime adapter, or tests | Needs provider config, UI, runtime adapter, and documentation |
| Accepts user-supplied API keys: OpenRouter | Implemented | OpenRouter is seeded as a custom-auth provider; backend stores encrypted keys and uses OpenRouter-compatible `chat/completions` requests | Production hardening still needs tenant isolation and stronger secrets lifecycle |
| Enumerates and can use 400+ models via plugin/config | Partially implemented (gaps) | OpenRouter now has startup refresh + manual refresh + UI browsing in Settings and Run Detail backed by the OpenRouter Models API with manual fallback | Still limited to OpenRouter only; no broader plugin/config registry or cross-provider catalog yet |
| Multi-model orchestration (routing, fallback, policy selection) | Partially implemented (gaps) | Routing now includes editable policies, latency/cost/success-aware scoring, Run Detail telemetry, Settings default policy selection, per-run policy selection, one fallback route, and explicit primary/fallback error reporting | Still needs richer policy editing, broader strategy types, deeper telemetry, and wider provider/model intelligence |
| Multi-agent workflows | Partially implemented (gaps) | Runs seed planner/reporter-style tasks and show workflow stages in the UI | Tasks are timeline records, not a true agent runtime with memory, tools, state transitions, or coordination |
| Audits code/apps/websites/scripts directly | Partially implemented (gaps) | Targets, runs, evidence capture, imports, findings, and reports are implemented | No built-in execution plane or scanner runner exists yet; current flow depends on imported or pasted results |
| Extensible with additional techniques | Partially implemented (gaps) | Flexible scanner import and provider configuration create extension points | No formal plugin registry, sandboxed tool runner, or enforced technique policy engine exists |

## Priority order requested

1. **A — OpenAI / Anthropic user-supplied custom key support**
2. **B — OpenRouter setup + model catalog direction**
3. **C — Multi-model routing and fallback**
4. **D — Real multi-agent runtime**
5. **E — Built-in audit execution / scanners**

## What is already closed from Priority A

The current repo now explicitly supports:

- encrypted custom key save / update / delete
- OpenAI custom key storage
- Anthropic custom key storage
- OpenRouter custom key storage
- runtime custom-key resolution before universal-key fallback
- regression coverage for encrypted provider key save / remove flows

## Recommended next implementation steps

### Next focus: Priority B
- expand from OpenRouter-only catalog to a broader provider model registry
- add richer browsing controls when needed (context, pricing, descriptions)
- define catalog refresh telemetry, stale-data handling, and provider health indicators
- keep preparing the transition into Priority C routing work

### After that: Priority C
- continue improving strategy depth, route health signals, and route observability
- add richer policy editing such as thresholds, weights, and validation rules
- keep building audit logging and operator-visible route history

### Longer-term roadmap
- multi-agent runtime with tool state and memory
- sandboxed scanner execution plane
- stronger production-grade secrets handling, auth, RBAC, and observability