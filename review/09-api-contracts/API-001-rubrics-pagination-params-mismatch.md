---
id: API-001
title: Frontend sends offset/limit to the rubrics list endpoint, which reads page/page_size
category: api-contracts
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
related: [ARCH-004]
child_of: null
affected_paths:
  - frontend/src/services/api.ts
  - frontend/src/stores/rubricStore.ts
  - backend/app/api/v1/rubrics.py
---

## Problem
`api.listRubrics` builds `offset`/`limit` query params; the backend endpoint accepts `page`/`page_size`. FastAPI silently ignores the unknown params, so every rubric list request returns page 1 with default size regardless of what the caller asked for.

## Evidence
- FE: `frontend/src/services/api.ts:241-247` (`query.set('offset', …)`, `query.set('limit', …)`).
- BE: `backend/app/api/v1/rubrics.py:125-130` (`page: int = 1, page_size: int = 20`).
- Every other FE list method uses `page`/`page_size` (e.g. `api.ts:97-99, 119-120, 143-146`) — rubrics is the outlier.

## Impact
Rubric pagination is broken (capped at the first 20); invisible until someone has >20 rubrics. Canonical example of hand-mirrored contract drift (ARCH-004).

## Root cause
FE method written against a different (perhaps planned) parameter convention; no type-level link to the backend.

## Proposed fix (specification)
Change `listRubrics` to `params?: { name?: string; page?: number; page_size?: number }` and set `page`/`page_size` like its siblings; update the one caller (`stores/rubricStore.ts`) accordingly.

## Alternatives considered
Support offset/limit server-side — rejected: would make rubrics the odd endpoint out instead.

## Verification
`npm test -- --run` (rubricStore tests updated); manual: seed 25 rubrics, page 2 reachable from the UI.

## Relationship notes
- `related: ARCH-004` — codegen would have made this a compile error; fix now, prevent later.
