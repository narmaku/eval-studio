---
id: BUG-014
title: Rubric generate/refine never pass the provider's API key to rubric-kit
category: bugs
severity: medium
effort: XS
confidence: high
breaking: false
status: open
depends_on: []
blocks: []
supersedes: []
superseded_by: []
conflicts_with: []
related: []
child_of: null
affected_paths:
  - backend/app/services/rubric_service.py
  - backend/app/api/v1/rubrics.py
---

## Problem
`/rubrics/generate` and `/rubrics/{id}/refine` resolve a provider profile but forward only `model` and `api_base` to rubric-kit — `provider.api_key` (resolved from `api_key_env`) is dropped. Generation against any key-protected endpoint (OpenAI et al.) fails with an authentication error unless the key happens to be in an env var litellm reads natively.

## Evidence
- Endpoints pass two fields: `backend/app/api/v1/rubrics.py:72-78` (`model=provider.default_model, api_base=provider.api_base`), `:216-222` (same for refine) — `provider.api_key` available via `core/providers.py:32-37`.
- Service forwards no key: `services/rubric_service.py:197-203` (`rubric_kit_generate(input_content=…, model=…, base_url=…, track_metrics=False)`), `:254-260` (refine).
- Proxy/SSL fields are likewise dropped (lower priority; note for the BUG-011 mechanism).

## Impact
The AI-assisted rubric feature — a headline capability in the README ("Design scoring rubrics — Create evaluation dimensions with AI assistance via rubric-kit") — only works for keyless/local endpoints or when the provider's `api_key_env` coincides with litellm's own default env var (e.g. a provider configured with `api_key_env: OPENAI_API_KEY` works *by accident* because litellm reads `OPENAI_API_KEY` itself; any custom env name fails).

## Root cause
The call signature mirrors a local-ollama development setup; key plumbing was never added.

## Proposed fix (specification)
1. Add `api_key: str | None` parameters to `generate_rubric`/`refine_rubric` (`rubric_service.py`) and forward them to `rubric_kit_generate`/`rubric_kit_refine` (the rubric-kit ≥0.2 API accepts an api key argument; confirm exact kwarg name — `api_key` — against the pinned version, and if absent, set it via litellm's per-call env shim documented by rubric-kit).
2. Pass `provider.api_key` at the two endpoint call sites (`rubrics.py:72-78, 216-222`).

## Alternatives considered
Document "judge provider must use litellm-native env names" — rejected: silently constrains a first-class feature.

## Verification
`tests/unit/test_rubric_service.py`: monkeypatch `rubric_kit.generate`, assert it receives the key for a provider with `api_key_env` set (set the env var via `monkeypatch.setenv`).

## Relationship notes
None beyond the noted overlap with BUG-011's mechanism for proxy/SSL (out of scope here).
