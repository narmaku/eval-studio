---
id: ARCH-008
title: Ad-hoc raw-SQL data migrations run in the FastAPI lifespan despite Alembic
category: architecture
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
related: [ARCH-002, INFRA-002, DATA-006]
child_of: null
affected_paths:
  - backend/app/main.py
---

## Problem
Two data migrations are implemented as raw SQL `UPDATE` statements executed on every application startup inside the lifespan, parallel to the Alembic migration system that exists for exactly this purpose. They run unconditionally forever, assume the tables exist (see INFRA-002), and one of them targets the dead `providers` table.

## Evidence
- `backend/app/main.py:16-32` — `_migrate_single_model_providers()`: `UPDATE providers SET single_model = 1 WHERE (default_model IS NULL OR default_model = '') AND single_model = 0`.
- `backend/app/main.py:35-51` — `_migrate_scored_sessions()`: `UPDATE sessions SET status = 'completed' WHERE status = 'ended' AND scores IS NOT NULL AND scores != 'null' AND length(scores) > 4`.
- Both called every boot: `main.py:66-67`.
- Alembic is configured and has 22 revisions (`backend/alembic/versions/`), including `1307fd3f3b27_add_single_model_to_providers.py` — the schema half of the first migration above already lives in Alembic; only the data half was put in the lifespan.

## Impact
Startup performs writes against the DB on every boot; migration logic has two homes with different guarantees (Alembic is versioned/once, lifespan is forever); the `length(scores) > 4` heuristic is fragile and re-evaluated eternally; fresh databases hit these statements before any schema exists (component of INFRA-002's startup crash).

## Root cause
Hotfixes for legacy rows (commits `ba97a3d`, `a311bd5`) were placed where they were easiest to ship rather than as Alembic data migrations.

## Proposed fix (specification)
1. DELETE `_migrate_single_model_providers` entirely (`main.py:16-32`, call at `:67`) — its target table is dead (ARCH-002); if ARCH-002 is deferred, move the statement into a one-shot Alembic revision instead.
2. Move `_migrate_scored_sessions`' statement into a new Alembic revision (`op.execute("UPDATE sessions SET status = 'completed' WHERE …")`) and DELETE the function + call (`main.py:35-51,66`).
3. Lifespan retains only logging configuration and the auth warning.

## Alternatives considered
1. Keep lifespan migrations but add an "applied" marker table — rejected: that is reimplementing Alembic.
2. Do nothing (statements are idempotent) — rejected: they still break fresh-DB startup ordering and normalize a second migration mechanism.

## Verification
- `cd backend && uv run alembic upgrade head` on a copy of a legacy DB → scored-ended sessions become `completed`.
- Start the app twice; startup logs contain no "Migrated …" lines; no writes occur at boot (verify with `PRAGMA data_version` before/after or sqlite trace).

## Relationship notes
- `related: ARCH-002` — step 1's deletion is also performed by ARCH-002; whichever lands first does it (both specs note the overlap; neither is fully superseded since step 2 here is independent).
- `related: INFRA-002` — removing boot-time writes eliminates the specific crash trigger on fresh DBs, but the schema-creation gap itself is INFRA-002's scope.
- `related: DATA-006` — if the migration chain is squashed, fold step 2's data fix into the squash boundary note there.
