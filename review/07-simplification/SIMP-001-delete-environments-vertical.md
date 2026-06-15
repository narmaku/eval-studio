---
id: SIMP-001
title: Delete the environments vertical — it is 100% stubs, 501s, and dead infra
category: simplification
severity: high
effort: M
confidence: high
breaking: true
status: open
depends_on: []
blocks: []
supersedes: [FE-005, DOC-003]
superseded_by: []
conflicts_with: []
related: [SIMP-006, DOC-001, DATA-001]
child_of: null
affected_paths:
  - backend/app/environments/
  - backend/app/api/v1/environments.py
  - backend/app/models/environment.py
  - backend/app/schemas/environment.py
  - backend/app/models/evaluation.py
  - frontend/src/pages/Environments.tsx
  - frontend/src/types/environment.ts
  - frontend/src/services/api.ts
  - environments/
  - backend/pyproject.toml
---

## Problem
The environments feature exists only as scaffolding: six REST endpoints that all raise 501, an `EnvironmentProvider` ABC with one stub implementation whose every method is a TODO, an ORM table nothing writes, FE pages/types/client methods targeting the 501 endpoints, a top-level `environments/` directory of compose/TMT/ansible templates nothing references, and the `asyncssh` dependency imported solely "to verify dependency is available". Docs and CLAUDE.md describe Compose and TMT providers that were never written.

## Evidence
- All endpoints 501: `backend/app/api/v1/environments.py:9-42`.
- Stub provider: `backend/app/environments/byoe.py:17-40` (three TODOs, fake `status="ready"`); `asyncssh` imported only for availability check (`byoe.py:4`); no other importer: `grep -rn "asyncssh" backend/app` → that one line.
- Dead table: `backend/app/models/environment.py`; `grep -rn "Environment" backend/app/api backend/app/services` → only the 501 router and `Evaluation.environment_id` passthrough.
- FE dead weight: `frontend/src/pages/Environments.tsx`, `types/environment.ts`, `api.ts:178-188` (six methods), route in `App.tsx:138-145`.
- Unreferenced infra: `environments/compose/*`, `environments/tmt/rhel9-provision.fmf`, `environments/ansible/README.md`, `environments/scenarios/*.yaml` — `grep -rn "scenarios/\|tmt/\|rhel9-base" backend frontend Makefile docker-compose.yml` → nothing (exception: `environments/rag-demo/` IS referenced by `docker-compose.yml:48-64`; it must be kept).
- Fictional docs: `docs/docs/environments.md:8-11` ("Supported providers include Docker Compose … and TMT"), CLAUDE.md directory tree.

## Impact
The largest single block of misleading surface in the repo: it makes the product look like it manages eval machines (it doesn't), pollutes the Evaluation model and create payloads with `environment_id`, costs a dependency (asyncssh), and every reviewer/agent reads ~20 files of vapor.

## Root cause
Aspirational scaffolding committed ahead of implementation; the roadmap moved on (RAG/arena/agent chat) and the scaffolding stayed.

## Proposed fix (specification)
Deletion list (file by file):
1. DELETE `backend/app/environments/` (base.py, byoe.py, __init__.py), `backend/app/api/v1/environments.py`, `backend/app/models/environment.py`, `backend/app/schemas/environment.py`; remove router include (`main.py:136,158`), model export (`models/__init__.py:5,19`).
2. Remove `asyncssh` from `backend/pyproject.toml:16` (with SIMP-006).
3. Drop `Evaluation.environment_id` column + `EvaluationCreate/Response.environment_id` + `RunRequest.environment_id` (alembic migration; coordinate with DATA-006 squash) — it is never consumed by any service (`grep -rn "environment_id" backend/app/services` → nothing).
4. DELETE FE: `pages/Environments.tsx`, `types/environment.ts`, the six `api.ts` methods (`:178-188`), nav entry in `components/layout/TopNav.tsx`, route block `App.tsx:18,138-145`; remove `environment_id`/`scenario_id` from `CreateSessionRequest` (`types/session.ts:81-82`).
5. DELETE `environments/compose/`, `environments/tmt/`, `environments/ansible/`, `environments/scenarios/` (keep `environments/rag-demo/`, used by compose `--profile rag`).
6. Rewrite `docs/docs/environments.md` to a single honest paragraph ("not yet built; tracked as future work") or delete the page + nav entry (`docs/mkdocs.yml`); covered by DOC-003.
7. Update CLAUDE.md tree (DOC-001).
Estimated deletion: ≈ 900 lines + 4 directories. Re-introduction later starts from a clean slate with a real provider.

## Alternatives considered
1. Implement BYOE properly — rejected here: that's a product decision; nothing in the current eval modes consumes environments, so even a working provider would be an island.
2. Keep the ABC, delete the rest — rejected: an interface with zero implementations is documentation, and false documentation at that.

## Verification
- `uv run pytest` green after removals (no tests target environments — itself telling).
- `npm run build` + `tsc --noEmit` green; no nav entry; `grep -rn "environment" frontend/src --include="*.ts*" -il` only matches unrelated words.
- App boots; OpenAPI no longer lists /environments.

## Relationship notes
- `supersedes: FE-005` — FE-005 is the frontend slice of this deletion; closes with it.
- `supersedes: DOC-003` — DOC-003's main content is the environments/adapters doc fiction; step 6 here plus DOC-001 absorb it. (If SIMP-001 is rejected, DOC-003 reopens as the honest-docs fallback.)
- `related: SIMP-006` (dependency removal), `DATA-001` (FK cleanup overlaps the dropped column), `DOC-001` (CLAUDE.md tree).
