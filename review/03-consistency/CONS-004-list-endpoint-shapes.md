---
id: CONS-004
title: List endpoints return two different shapes (paginated envelope vs bare array)
category: consistency
severity: low
effort: S
confidence: high
breaking: true
status: open
depends_on: []
blocks: []
supersedes: []
superseded_by: []
conflicts_with: []
related: [DUP-009, ARCH-004]
child_of: null
affected_paths:
  - backend/app/api/v1/providers.py
  - backend/app/api/v1/harnesses.py
  - backend/app/api/v1/tool_servers.py
  - backend/app/api/v1/evaluators.py
  - backend/app/api/v1/artifacts.py
  - backend/app/api/v1/judges.py
  - frontend/src/services/api.ts
---

## Problem
DB-backed resources list as `PaginatedResponse{items,total,page,page_size,pages}` while registry/file-backed resources (providers, harnesses, tool-servers, evaluators, artifacts, judge presets) return bare JSON arrays. Clients must know per-resource which shape to expect.

## Evidence
- Paginated: `api/v1/evaluations.py:70-77`, `datasets.py:83-89`, `results.py:31-37`, `sessions.py:27-35`, `rubrics.py:124-130`, `api_keys.py:81-86`.
- Bare arrays: `providers.py:185-189`, `harnesses.py:53-63`, `tool_servers.py:53-62`, `evaluators.py:51-67`, `artifacts.py:33-43`, `judges.py:75-101` (presets).

## Impact
FE/SDK code paths fork per resource; future cross-cutting features (total counts, paging controls) can't be added uniformly.

## Root cause
Registry resources are small and unpaginated by nature; nobody decided a convention.

## Proposed fix (specification)
Adopt the rule: **collections that live in the DB paginate; bounded config collections return bare arrays** — i.e. keep today's split but make it a written rule, OR wrap everything. Recommended: keep the split (registry collections are O(10) and pagination there is ceremony), and:
1. Document the rule in `docs/docs/api-reference.md` and in `backend/app/schemas/common.py` docstring.
2. Fix the one genuine offender: `GET /artifacts` is DB-backed and unbounded per evaluation → switch to `PaginatedResponse[ArtifactResponse]` (breaking; FE `listArtifacts` in `api.ts:344-345` and `ArtifactsList.tsx` adjust to `.items`).

## Alternatives considered
Paginate everything — rejected: adds page plumbing to five config UIs for collections of ~5 entries.

## Verification
`uv run pytest tests/integration/test_artifacts_api.py` updated; FE `ArtifactsList.test.tsx` updated; rule text present in api-reference.

## Relationship notes
- `related: DUP-009` — same routers; combine edits.
- `related: ARCH-004` — shape change flows into generated FE types automatically if ARCH-004 lands first.
