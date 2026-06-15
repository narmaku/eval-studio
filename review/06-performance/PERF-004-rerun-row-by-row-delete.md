---
id: PERF-004
title: Rerun deletes results by loading and deleting rows one at a time
category: performance
severity: trivial
effort: XS
confidence: high
breaking: false
status: open
depends_on: []
blocks: []
supersedes: []
superseded_by: []
conflicts_with: []
related: [BUG-015]
child_of: null
affected_paths:
  - backend/app/api/v1/evaluations.py
---

## Problem
`rerun_evaluation` selects all `Result` rows into ORM objects and issues `db.delete()` per row — N SELECT-hydrations and N DELETE statements where one bulk DELETE suffices.

## Evidence
`backend/app/api/v1/evaluations.py:351-354`:
```python
existing_results = await db.execute(select(Result).where(Result.evaluation_id == evaluation_id))
for r in existing_results.scalars().all():
    await db.delete(r)
```

## Impact
Sub-second until evaluations have thousands of results; mostly a correctness-of-idiom fix.

## Root cause
ORM-habit deletion.

## Proposed fix (specification)
```python
from sqlalchemy import delete
await db.execute(delete(Result).where(Result.evaluation_id == evaluation_id))
```
(Fold into the same edit as BUG-015's artifact cleanup.)

## Alternatives considered
None needed.

## Verification
`tests/integration/test_evaluations.py` rerun test green; query log shows a single DELETE.

## Relationship notes
- `related: BUG-015` — same endpoint, same PR.
