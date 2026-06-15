---
id: CONS-001
title: .env.example documents variables the Settings class does not have (and vice versa)
category: consistency
severity: medium
effort: S
confidence: high
breaking: false
status: open
depends_on: []
blocks: []
supersedes: []
superseded_by: []
conflicts_with: []
related: [ARCH-005, INFRA-006, DOC-001]
child_of: null
affected_paths:
  - .env.example
  - backend/app/core/config.py
  - backend/app/services/provider_utils.py
---

## Problem
`.env.example` is the user's contract for configuration, and it has drifted from `Settings` in both directions: it documents `LITELLM_MODEL` and `LITELLM_API_BASE`, which don't exist as settings (the actual setting is `default_model`, env var `DEFAULT_MODEL`; there is no API-base setting at all), while real settings (`ARTIFACTS_DIR`, `RUN_TIMEOUT_DEFAULT`, `RUN_TIMEOUT_MAX`) are undocumented. It also carries a "Planned / Future" section of variables nothing reads.

## Evidence
- `.env.example:36-40` — `# LITELLM_MODEL=gpt-4.1`, `# LITELLM_API_BASE=http://localhost:4000`.
- `backend/app/core/config.py:24-25` — fields are `litellm_api_key` and `default_model`; no `litellm_model`, no `litellm_api_base` (and `extra="ignore"` at `:12` means the documented vars are silently dropped).
- Stale docstring keeps the myth alive: `backend/app/services/provider_utils.py:50` — "3. Settings fallback (LITELLM_MODEL, LITELLM_API_KEY env vars)".
- Undocumented real settings: `config.py:43-47` (`artifacts_dir`, `run_timeout_default`, `run_timeout_max`).
- Vapor section: `.env.example:112-124` (`BACKEND_HOST/PORT`, `TESTING_FARM_*`, `MLFLOW_TRACKING_URI` — `grep -rn "TESTING_FARM\|MLFLOW" backend/app` → no hits).
- `docker-compose.yml:56` even forwards `LITELLM_MODEL` into the rag-demo container, where `environments/rag-demo/app.py` is the only real consumer — i.e. the variable documented as the backend's default model only affects a demo container.

## Impact
A user who sets `LITELLM_MODEL=gpt-4.1` per the instructions gets no default model; judge resolution then fails with "No judge model configured" with no hint why. This is a first-run footgun.

## Root cause
The setting was renamed (`litellm_model` → `default_model`, mirrored by migration `416da1255d27` for the dead table) without updating the env contract.

## Proposed fix (specification)
1. Decide the canonical env names and make code and docs match. Recommended: keep `LITELLM_API_KEY`, rename the setting `default_model` → keep but add alias so both `DEFAULT_MODEL` and nothing else; document `DEFAULT_MODEL` in `.env.example` and delete `LITELLM_MODEL`/`LITELLM_API_BASE` lines (an API-base default doesn't exist — either add `default_api_base: str | None` to Settings and thread it through `resolve_model_config`'s fallback branch (`provider_utils.py:99-103`), or drop the concept; recommended: drop, providers own api_base).
2. Add the missing real settings to `.env.example` (artifacts dir, run timeouts, with defaults).
3. DELETE the "Planned / Future" section (`.env.example:112-124`).
4. Fix the docstring at `provider_utils.py:46-51`.
5. Coordinate wording of the registry-path block (`.env.example:67-82`) with ARCH-005's final variable names.

## Alternatives considered
Add `LITELLM_MODEL` as a validation alias on `default_model` — defensible for back-compat, but the project has no users to keep compatible; one name is simpler.

## Verification
- `cp .env.example .env`, set `DEFAULT_MODEL=ollama/llama3`, start app, create a QA eval without judge provider → judge resolves to the default (exercises `provider_utils.py:170-174`).
- A script/test that asserts every non-comment key in `.env.example` is consumed: present in `Settings.model_fields` (by env name) or in the ARCH-005 registry list.

## Relationship notes
- `related: ARCH-005` — registry path variables move into Settings there; this issue owns the documentation file's overall truthfulness.
- `related: INFRA-006` — sibling stale-example problem for `providers.yaml.example`.
- `related: DOC-001` — CLAUDE.md repeats the `LITELLM_MODEL`/`LITELLM_API_KEY` claim ("switching… by changing the LITELLM_MODEL and LITELLM_API_KEY environment variables") and must be updated to the canonical names chosen here.
