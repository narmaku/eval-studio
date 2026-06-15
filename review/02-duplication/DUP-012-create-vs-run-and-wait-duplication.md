---
id: DUP-012
title: create_evaluation and run_and_wait duplicate validation and Evaluation construction
category: duplication
severity: low
effort: XS
confidence: high
breaking: false
status: open
depends_on: []
blocks: []
supersedes: []
superseded_by: []
conflicts_with: []
related: [ARCH-001, BUG-016]
child_of: null
affected_paths:
  - backend/app/api/v1/evaluations.py
---

## Problem
The dataset-exists check, the arena ≥2-contestants check, and the `Evaluation(...)` construction + commit appear identically in `create_evaluation` and `run_and_wait`.

## Evidence
`backend/app/api/v1/evaluations.py:42-65` vs `:167-191` — same three blocks (dataset check `:43-46`/`:167-170`, arena check `:48-52`/`:172-176`, construction `:54-65`/`:178-191`).

## Impact
Two validation paths can drift (e.g. a future "dataset must have items" rule added to one); ~35 duplicated lines.

## Root cause
`run_and_wait` written as create+run in one endpoint without extracting the shared step.

## Proposed fix (specification)
1. `async def _create_validated_evaluation(payload: EvaluationCreate | RunRequest, db) -> Evaluation` module-level helper containing the three blocks (both payload types expose the same fields used here).
2. Both endpoints call it; DELETE the inline copies.

## Alternatives considered
Have `run_and_wait` call the `create_evaluation` endpoint function — rejected: entangles response models and logging.

## Verification
`uv run pytest tests/integration/test_evaluations.py tests/integration/test_run_endpoint.py` green.

## Relationship notes
- `related: ARCH-001` — ARCH-001 touches the same file's run-dispatch half; this touches the create half; combine in one PR if convenient.
- `related: BUG-016` — the duplicate-run race fix modifies the run side of these endpoints; no ordering constraint.
