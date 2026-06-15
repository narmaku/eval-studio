---
id: ARCH-002
title: Providers have two storage systems; the database one is dead but still shapes the codebase
category: architecture
severity: high
effort: M
confidence: high
breaking: true
status: open
depends_on: []
blocks: [DATA-006, DUP-010, TEST-002]
supersedes: [CONS-007]
superseded_by: []
conflicts_with: []
related: [DUP-010, BUG-007, ARCH-005]
child_of: null
affected_paths:
  - backend/app/models/provider.py
  - backend/app/services/provider_utils.py
  - backend/app/core/providers.py
  - backend/app/main.py
  - backend/alembic/versions/
  - backend/tests/unit/test_provider_model.py
  - backend/tests/unit/test_providers.py
---

## Problem
Provider profiles exist twice: a YAML-backed registry (`core/providers.py`, served by `/api/v1/providers`) and a SQLAlchemy `Provider` table. The DB side is dead — no endpoint creates or updates rows — yet it retains a model, ~6 migrations (including two merge revisions), a startup raw-SQL data migration, a YAML↔ORM converter (`resolve_provider`) with **zero callers**, and unit tests. Two sources of truth for the most central config object in the product.

## Evidence
- YAML registry + CRUD API: `backend/app/core/providers.py:40-148`, `backend/app/api/v1/providers.py:185-244` (all operations go to `provider_registry`).
- Dead ORM model: `backend/app/models/provider.py:15-34`.
- Sole reader has no callers: `grep -rn "resolve_provider\b" backend/app` → only the definition at `backend/app/services/provider_utils.py:326`.
- Converter papers over schema drift with `getattr(db_provider, "default_params", None)` for a column that doesn't exist on the model (`provider_utils.py:367`).
- Startup data migration for the dead table: `backend/app/main.py:16-32` (`UPDATE providers SET single_model = 1 …`).
- Migrations dedicated to the table: `f1197de8eb37_add_providers_table.py`, `2a778187e3d6_add_ssl_fields…`, `3fc49606c57f_add_rate_limit_fields…`, `416da1255d27_rename_litellm_model…`, `a1b2c3d4e5f6_add_custom_provider_fields.py`, `a3b4c5d6e7f8_drop_purpose…`, `1307fd3f3b27_add_single_model…`, plus merge heads `ba5ca10b45b6`, `d18fbfc6a959`.

## Impact
Every provider feature (rate limits, SSL, single_model…) was implemented twice (column + dataclass field) and migrated once for a table nobody reads. The lifespan migration runs on every boot against dead data. New contributors must figure out which store is real. `resolve_provider`'s defensive `getattr` style hides drift instead of failing.

## Root cause
The product started with DB-backed providers (see migration history), later switched to the YAML registry for portability, and the DB vertical was never deleted.

## Proposed fix (specification)
Make the YAML registry the single store; delete the DB vertical.

1. DELETE `backend/app/models/provider.py`; remove `Provider` from `backend/app/models/__init__.py`.
2. DELETE `resolve_provider()` from `backend/app/services/provider_utils.py:326-376` (and its `Provider` import at line 18, plus the now-unused `AsyncSession`/`select` imports if orphaned).
3. DELETE `_migrate_single_model_providers()` and its call from `backend/app/main.py:16-32,67`.
4. Add one final alembic migration `drop_providers_table` (`op.drop_table("providers")`). Do not rewrite history; the early-stage alternative — squashing all 22 migrations into one initial schema — is recorded in DATA-006 and is the recommended companion.
5. DELETE `backend/tests/unit/test_provider_model.py`; prune any `resolve_provider` tests from `tests/unit/test_providers.py` / `test_provider_utils.py`.
6. Breaking change: any pre-existing local DB rows in `providers` are abandoned. Acceptable per project stage; release note: "re-create providers via Settings → Providers (config/providers.yaml)".

Estimated deletion: ≈ 300 lines source + ≈7 migration files if DATA-006 squash also lands.

## Alternatives considered
1. Move providers fully into the DB and delete the YAML registry — rejected: the YAML registry is the live, tested path, three sibling registries already use YAML, and file-based config is git-diffable for an internal tool.
2. Keep both "for flexibility" — rejected: that is the current bug-generating state.

## Verification
- `uv run pytest` green after deletions.
- `grep -rn "models.provider\|resolve_provider" backend/` → no hits.
- Boot the app against an existing dev DB: startup log no longer prints "Migrated single-model providers"; provider CRUD via UI still works and persists to `config/providers.yaml`.

## Relationship notes
- `supersedes: CONS-007` — the defensive-getattr inconsistency exists only inside `resolve_provider`; deleting the function removes the pattern, closing CONS-007 without action.
- `blocks: DATA-006` — the migration-chain cleanup must happen after (or together with) the table drop so the squashed schema doesn't recreate `providers`.
- `related: DUP-010` — the 4-way provider shape duplication drops to 3 shapes after this issue; DUP-010 handles the rest.
- `related: BUG-007` (create_provider drops `single_model`) — fix lands in the YAML path and is unaffected by this deletion; listed because both touch provider persistence.
- `related: ARCH-005` — both are "two mechanisms for one concern" problems; no ordering constraint.
