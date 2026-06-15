---
id: ARCH-004
title: API types are hand-maintained in three places (backend Pydantic, frontend TS, clients Pydantic)
category: architecture
severity: medium
effort: M
confidence: high
breaking: false
status: open
depends_on: []
blocks: []
supersedes: [API-003]
superseded_by: []
conflicts_with: []
related: [ARCH-003, API-001, API-004, SIMP-004, DUP-010]
child_of: null
affected_paths:
  - frontend/src/types/
  - backend/app/schemas/
  - clients/src/eval_studio/models.py
---

## Problem
Every API shape is written by hand three times: backend Pydantic schemas, ~14 frontend type modules, and the `clients/` SDK's Pydantic models. The backend already serves `/api/v1/openapi.json`, but nothing consumes it. Drift is not hypothetical — several mismatches exist right now (API-001, API-003, API-004, ARCH-003), and the FE source itself carries TODOs asking for generation.

## Evidence
- FE TODO: `frontend/src/types/session.ts:1-2` — "Consider generating these types from the FastAPI OpenAPI spec using openapi-typescript".
- OpenAPI exposed: `backend/app/main.py:77` (`openapi_url="/api/v1/openapi.json"`).
- Existing drift instances: `frontend/src/services/api.ts:241-247` (rubrics `offset/limit` vs backend `page/page_size`, `backend/app/api/v1/rubrics.py:125-130`); `api.ts:140` types replay as `Session` while backend returns `SessionReplayResponse` (`backend/app/schemas/session.py`); `api.ts:175-176` types import response as `Dataset` while the endpoint may return a list (`backend/app/api/v1/dataset_import.py:168`).
- Third mirror: `clients/src/eval_studio/models.py` (Evaluation/Dataset/Result/… re-declared).

## Impact
Three places to update per API change; the compiler can't catch cross-repo drift, so it ships (broken rubric pagination is live today). Review effort triples.

## Root cause
SPA and SDK were built against an evolving API without ever wiring up the generator mentioned in the FE TODO.

## Proposed fix (specification)
1. Add `openapi-typescript` as a frontend devDependency and a script:
   `"gen:api": "openapi-typescript http://localhost:8000/api/v1/openapi.json -o src/types/generated/api.d.ts"` (plus a checked-in snapshot so CI/builds don't need a live server: generate from `uv run python -c "import json; from app.main import app; print(json.dumps(app.openapi()))"`).
2. Re-export domain aliases from `src/types/index.ts` (`type Evaluation = components['schemas']['EvaluationResponse']`, …) and migrate `src/types/*.ts` module-by-module, deleting hand-written interfaces as they're replaced. FE-only concepts (UI state, WS envelopes until ARCH-003 lands) stay hand-written.
3. CI: add a job step that regenerates and `git diff --exit-code`s the snapshot, so backend schema changes that would break the FE fail loudly.
4. `clients/` models: covered by SIMP-004 (delete the package). If SIMP-004 is rejected, generate the client from OpenAPI instead of hand-writing (e.g. switch models.py to `datamodel-code-generator` output) — record that choice in ROADMAP.

## Alternatives considered
1. Keep hand-written types, add contract tests — rejected: tests must also be hand-written per endpoint; generation makes the whole class of bug impossible.
2. tRPC-style runtime sharing — rejected: wrong stack (Python backend).

## Verification
- `npm run gen:api && tsc --noEmit` passes; intentionally rename a backend schema field and confirm `tsc` now fails.
- The API-001/API-003 mismatches become type errors during migration and get fixed as part of this work.

## Relationship notes
- `supersedes: API-003` — the replay/import-response type mismatches are exactly what step 2's migration fixes; once generated types are in place API-003 needs no separate action.
- `related: API-001, API-004` — those involve behavior (query params, phantom enum members), not just types; generation surfaces them but the fixes are specified there.
- `related: ARCH-003` — WS envelopes get Pydantic models there, which then ride this pipeline.
- `related: SIMP-004` — decides the fate of the third mirror.
- `related: DUP-010` — provider shape consolidation reduces what needs generating.
