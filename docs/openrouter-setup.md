# OpenRouter Setup Notes

This document captures the current OpenRouter integration shape in the repo and the next steps for making it production-grade.

## Current repo behavior

OpenRouter is currently supported as a custom-auth provider in the application.

### What the app already expects
- `auth_mode: custom`
- a user-supplied API key stored encrypted at rest
- `base_url` set to `https://openrouter.ai/api/v1`
- model passed as a provider/model string such as `openai/gpt-4.1-mini`

### Runtime request shape
The backend uses an OpenAI-compatible chat completions request against:

```text
POST https://openrouter.ai/api/v1/chat/completions
```

with headers like:

```text
Authorization: Bearer <OPENROUTER_API_KEY>
Content-Type: application/json
```

## Recommended setup steps

1. Create an OpenRouter account and generate an API key
2. In **Settings**, switch OpenRouter to **Custom** auth mode
3. Set the base URL to:

```text
https://openrouter.ai/api/v1
```

4. Save the API key in the custom key field
5. Choose a model string supported by OpenRouter

## Recommended optional headers

OpenRouter documentation recommends sending these headers when appropriate:

- `HTTP-Referer`
- `X-OpenRouter-Title`

The current repo does **not** send these headers yet. They are a good follow-up enhancement for analytics and provider-side app attribution.

## Current limitations

- no automatic OpenRouter model catalog sync yet
- no model discovery UI yet
- no routing or fallback layer yet
- no per-tenant secret context yet

## Suggested next build steps

### 1. Model catalog ingestion
- fetch OpenRouter Models API on a schedule
- store normalized model metadata in the database
- surface searchable model choices in Settings and Run Detail

### 2. Safer secrets handling
- move from app-level storage only to dedicated secret management / rotation for production

### 3. Routing support
- define routing groups like `fast_triage` and `deep_reasoning`
- add fallback providers / models per policy

## Source notes used for this setup

Recent OpenRouter documentation confirms:

- Bearer token authentication is required
- the OpenAI-compatible chat completions endpoint is supported
- `HTTP-Referer` and `X-OpenRouter-Title` are recommended optional headers

This repo document intentionally keeps setup guidance aligned to the current application rather than overpromising future routing/catalog behavior.