---
id: PERF-001
title: Evaluation relationships eager-load all results/sessions/artifacts on every list query
category: performance
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
related: [ARCH-001]
child_of: null
affected_paths:
  - backend/app/models/evaluation.py
  - backend/app/api/v1/evaluations.py
  - backend/app/services/evaluation_service.py
---

## Problem
`Evaluation.results`, `.sessions`, and `.artifacts` are declared `lazy="selectin"`, so *every* `select(Evaluation)` — including the paginated list endpoint — triggers three extra queries that pull **all result rows** (including full `actual_answer`/`judge_reasoning` text) for every evaluation on the page. The list endpoint then computes its stats via a separate aggregate query anyway, so the eager-loaded rows are fetched and discarded.

## Evidence
- `backend/app/models/evaluation.py:26-32` (`lazy="selectin"` ×3).
- List endpoint loads pages of 20 evaluations (`api/v1/evaluations.py:92-94`) and separately aggregates stats (`:96-120`) — the selectin rows are unused.
- Same waste in every service load of a single evaluation (`evaluation_service.py:32`) where only `dataset.items` is needed, not the evaluation's previous results.

## Impact
A workspace with 50 evaluations × 200 results makes the dashboard list fetch ~10,000 large text rows to render 20 cards. SQLite tolerates it locally but page latency grows linearly with history; this is the most realistic perf cliff in the app's normal usage.

## Root cause
Eager loading chosen as a convenience default when the model was written; the access patterns that actually need the collections (`dataset.items` in services) were generalized to all relationships.

## Proposed fix (specification)
1. Change the three relationships to `lazy="raise"` (or drop `lazy` to default `select` if any legitimate lazy access remains — audit shows none under async, where implicit lazy loads raise anyway).
2. Where collections are genuinely needed, load explicitly:
   - `delete_evaluation` cascade works at the DB level via `cascade="all, delete-orphan"` — verify delete still works with `lazy="raise"` by using `await db.execute(delete(Result).where(...))`-style explicit deletes or `selectinload` on that one query.
   - Dataset items in services already come from `Dataset.items` (separate model, keep as is or apply the same treatment with explicit `selectinload(Dataset.items)` in the three service loads).
3. Re-run the integration suite; each `MissingGreenlet`/raise flags a hidden implicit load to make explicit.

## Alternatives considered
Keep selectin but add `noload` options per query — rejected: opt-out at every call site is exactly how this regresses.

## Verification
- `tests/integration/test_evaluations.py` extended: with `echo=True` capture, list endpoint executes exactly 2 queries (page + count) + 1 stats aggregate — no per-evaluation result loads.
- Manual: seed 50 evals × 200 results; `GET /api/v1/evaluations` latency unchanged vs empty DB (today it isn't).

## Relationship notes
- `related: ARCH-001` — service-side loads move into the consolidated runner; coordinate the explicit `selectinload(Dataset.items)` there.
