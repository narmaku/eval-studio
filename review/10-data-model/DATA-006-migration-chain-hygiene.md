---
id: DATA-006
title: 22-revision migration chain with two merge heads, ~7 revisions for a dead table — squash to one initial schema
category: data-model
severity: low
effort: S
confidence: high
breaking: true
status: open
depends_on: [ARCH-002]
blocks: []
supersedes: []
superseded_by: []
conflicts_with: []
related: [ARCH-008, DATA-001, DATA-003, DATA-005, SIMP-001]
child_of: null
affected_paths:
  - backend/alembic/versions/
---

## Problem
For a pre-1.0 product with no external deployments, the Alembic chain already has 22 revisions including two merge commits (`ba5ca10b45b6_merge_ssl_and_artifacts_heads`, `d18fbfc6a959_merge_custom_provider_and_rename_heads`) and at least seven revisions that exist solely to evolve the dead `providers` table. Several open issues (DATA-001 FKs, DATA-003 tz columns, DATA-005 table drop, SIMP-001 column drop) would each add more.

## Evidence
`ls backend/alembic/versions/` — 22 files; providers-only chain: `f1197de8eb37`, `2a778187e3d6`, `3fc49606c57f`, `416da1255d27`, `a1b2c3d4e5f6`, `a3b4c5d6e7f8`, `1307fd3f3b27`; merges as named above.

## Impact
Fresh installs replay 22 steps to build 10 tables (one of them dead); merge heads signal the chain already bit-rotted once; every structural issue in this review pays migration tax individually.

## Root cause
Normal accretion, never compacted; parallel branches created the merge heads.

## Proposed fix (specification)
After the schema-changing issues land (or bundled with them):
1. Generate one new initial revision from current metadata (`alembic revision --autogenerate` against an empty DB with all model changes applied), incorporating: no `providers` table (ARCH-002), no `environments` table/`environment_id` (SIMP-001), FKs (DATA-001), `timezone=True` (DATA-003), no `judge_configs` if DATA-005 lands.
2. DELETE all 22 old revision files.
3. Migration story for existing dev DBs: document `alembic stamp head` after manual verification, or accept recreate-from-scratch (project stage allows it; the only data anyone has is local experiments). Keep ARCH-008's sessions data-fix semantics by folding it into a release note ("re-run scoring on legacy sessions if needed").
4. Breaking change: old DBs can't migrate forward automatically. Explicitly acceptable now; never again after first tagged release — say so in CONTRIBUTING.

## Alternatives considered
Keep the chain and just add new revisions — the default if any deployment exists that can't be recreated; ROADMAP should confirm none does.

## Verification
- `rm dev DB && uv run alembic upgrade head` builds the schema in one step; `uv run alembic check` (or autogenerate diff) shows empty diff vs models.
- INFRA-002's startup migration works against the squashed chain.

## Relationship notes
- `depends_on: ARCH-002` — the squash must encode the post-deletion schema; squashing first would recreate the dead table.
- `related: DATA-001, DATA-003, DATA-005, SIMP-001, ARCH-008` — all contribute schema deltas the squash absorbs; sequence them before it in the roadmap.
