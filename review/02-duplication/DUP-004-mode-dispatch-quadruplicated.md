---
id: DUP-004
title: Evaluation-mode dispatch if/elif duplicated at four call sites
category: duplication
severity: low
effort: XS
confidence: high
breaking: false
status: open
depends_on: []
blocks: []
supersedes: []
superseded_by: [ARCH-001]
conflicts_with: []
related: [CONS-002]
child_of: ARCH-001
affected_paths:
  - backend/app/api/v1/evaluations.py
  - backend/app/services/run_service.py
---

## Problem
The `if mode == "arena": run_arena… elif mode == "rag": run_rag… else: run_qa…` block is written four times, three of them inside near-identical `_run_in_background` closures in the same router file.

## Evidence
`api/v1/evaluations.py:198-205` (run_and_wait async branch), `:317-324` (run endpoint), `:362-369` (rerun endpoint); `services/run_service.py:47-52` (sync execution).

## Impact
A new mode (or a renamed one) needs four synchronized edits; the string literals also bypass the `EvaluationMode` enum (CONS-002).

## Root cause
Symptom of ARCH-001 (no single runner entrypoint).

## Proposed fix (specification)
None standalone — ARCH-001 step 4 replaces all four with one `MODE_RUNNERS` lookup behind `run_evaluation(evaluation_id, db)`. The three background-task closures in `evaluations.py` collapse to one shared `def _spawn_run(evaluation_id: str) -> None` helper.

## Alternatives considered
Extract just the closure into a module-level helper now — fine as a quick win, but ARCH-001 deletes it anyway.

## Verification
`grep -n "run_arena_evaluation\|run_rag_evaluation\|run_qa_evaluation" backend/app/api backend/app/services/run_service.py` → only the runner module.

## Relationship notes
- `superseded_by: ARCH-001` / `child_of: ARCH-001` — symptom record; closes with the consolidation.
- `related: CONS-002` — same literals problem; CONS-002 covers the enum usage broadly.
