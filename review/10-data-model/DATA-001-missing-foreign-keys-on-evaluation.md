---
id: DATA-001
title: Evaluation reference columns lack ForeignKey constraints
category: data-model
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
related: [SIMP-001, DATA-006]
child_of: null
affected_paths:
  - backend/app/models/evaluation.py
  - backend/alembic/versions/
---

## Problem
`Evaluation.dataset_id`, `.environment_id`, and `.judge_config_id` are plain `String(36)` columns with no `ForeignKey`, while every other reference in the schema (`Result.evaluation_id`, `DatasetItem.dataset_id`, `Session.evaluation_id`, `Artifact.evaluation_id`) is a real FK. SQLite FK enforcement is even switched on globally (`PRAGMA foreign_keys=ON`), but these columns opt out — deleting a dataset leaves evaluations pointing at nothing, and services compensate with "dataset not found → mark failed" runtime checks.

## Evidence
- `backend/app/models/evaluation.py:21-23` (bare `String(36)` ×3) vs `models/result.py:10-12`, `models/dataset.py:33`, `models/session.py:16`, `models/artifact.py:10` (proper `ForeignKey`).
- FK pragma on: `core/database.py:16-21`.
- Runtime compensation: `services/evaluation_service.py:54-62`.

## Impact
Dangling references are representable and occur on dataset deletion (no RESTRICT/SET NULL); integrity bugs surface as mid-run failures instead of 4xx at mutation time.

## Root cause
Columns added before referenced tables stabilized; never tightened.

## Proposed fix (specification)
1. `dataset_id` → `ForeignKey("datasets.id", ondelete="RESTRICT")` (an evaluation's dataset shouldn't vanish; surface a 409 in `delete_dataset` when referenced — add that check + test).
2. `judge_config_id` → `ForeignKey("judge_configs.id", ondelete="SET NULL")` (judge deletion is benign; resolution falls back).
3. `environment_id` — dropped entirely by SIMP-001; if SIMP-001 is rejected, FK it like dataset_id.
4. Alembic migration with `batch_alter_table` (SQLite); pre-clean orphans first (`UPDATE evaluations SET judge_config_id=NULL WHERE judge_config_id NOT IN (SELECT id FROM judge_configs)`, analogous check-and-fail for dataset orphans).

## Alternatives considered
Application-level checks only (status quo) — rejected: the engine enforces FKs everywhere else; partial enforcement is the worst of both.

## Verification
- Migration applies on a seeded legacy DB copy.
- Integration: delete a dataset referenced by an evaluation → 409; delete a judge config → evaluation's `judge_config_id` nulled, run falls back per `resolve_judge_config`.

## Relationship notes
- `related: SIMP-001` — decides `environment_id`'s fate; do SIMP-001 first to avoid FK-ing a column that's about to be dropped.
- `related: DATA-006` — if the migration chain is squashed, fold these constraints into the squashed initial schema instead of a new revision.
