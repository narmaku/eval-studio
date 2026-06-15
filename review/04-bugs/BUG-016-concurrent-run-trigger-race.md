---
id: BUG-016
title: Concurrent run/rerun triggers can double-execute an evaluation
category: bugs
severity: low
effort: S
confidence: medium
breaking: false
status: open
depends_on: []
blocks: []
supersedes: []
superseded_by: []
conflicts_with: []
related: [ARCH-001, DUP-012]
child_of: null
affected_paths:
  - backend/app/api/v1/evaluations.py
  - backend/app/services/evaluation_service.py
---

## Problem
The run endpoints check status in the request handler, then reset to `pending`, then spawn a background task which re-checks `status != "pending"` before setting `running`. Two concurrent POSTs both pass the handler check (both see `pending`/`failed`), both commit `pending`, and both background tasks can read `pending` before either commits `running` — duplicate execution, duplicated Result rows, interleaved WS streams. The rerun endpoint widens the window by also deleting results first.

## Evidence
- Handler check + reset + spawn: `backend/app/api/v1/evaluations.py:296-330` (`/run`), `:334-376` (`/rerun`).
- Background guard not atomic: `services/evaluation_service.py:37-43` — read (`scalar_one_or_none`) then `status = "running"; commit` with an await gap; same in arena/rag copies.
- SQLite WAL allows the two readers to proceed; no `UPDATE … WHERE status='pending'` style compare-and-set anywhere.

## Impact
Double-clicks or FE retries can double-run (double LLM cost, duplicate results). Window is small (`medium` confidence on real-world frequency, race is structurally present).

## Root cause
Status used as a lock without an atomic transition.

## Proposed fix (specification)
Make the pending→running transition a compare-and-set, in one place (post-ARCH-001 runner; today in each service):
```python
result = await db.execute(
    update(Evaluation)
    .where(Evaluation.id == evaluation_id, Evaluation.status == "pending")
    .values(status="running")
)
await db.commit()
if result.rowcount == 0:
    logger.warning("evaluation.already_claimed", evaluation_id=evaluation_id)
    return
```
The losing task exits before doing any work. The handler-side checks remain as fast-path UX validation only.

## Alternatives considered
asyncio.Lock keyed by evaluation_id — works single-process but the CAS also covers any future multi-worker deployment and is fewer moving parts.

## Verification
Unit: two concurrent `run_qa_evaluation` invocations against one pending evaluation (patched `call_model`) → exactly one set of Results, one "skipped/already_claimed" log.

## Relationship notes
- `related: ARCH-001` — fix belongs in the consolidated runner's claim step; implement there if ARCH-001 lands first.
- `related: DUP-012` — same router file; independent.
