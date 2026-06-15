---
id: API-004
title: The 'cancelled' evaluation status exists in both enums and all FE handling, but nothing can ever set it
category: api-contracts
severity: medium
effort: S
confidence: high
breaking: true
status: open
depends_on: []
blocks: [FE-002]
supersedes: []
superseded_by: []
conflicts_with: []
related: [CONS-002]
child_of: null
affected_paths:
  - backend/app/schemas/evaluation.py
  - frontend/src/types/evaluation.ts
  - frontend/src/stores/evaluationStore.ts
  - frontend/src/pages/QAEvaluation.tsx
  - frontend/src/components/evaluation/EvaluationProgress.tsx
---

## Problem
`EvaluationStatus.CANCELLED` is declared, the FE types include it, three FE code paths handle it (polling terminal check, WS status terminal check, completion toast "Evaluation was cancelled") — but no backend code path assigns `cancelled`, and there is no cancel endpoint. The status is pure fiction that nonetheless shapes UI logic, and it underwrites the lying Cancel button (FE-002).

## Evidence
- Enum member: `backend/app/schemas/evaluation.py:20`; `grep -rn "cancelled\|CANCELLED" backend/app --include="*.py"` → only the enum declaration.
- FE handling: `frontend/src/stores/evaluationStore.ts:134-138, 201-206, 220-225`; `pages/QAEvaluation.tsx:136-144`; `components/evaluation/EvaluationProgress.tsx:19,27,48`.

## Impact
Dead branches in five FE locations; contributors reasonably assume cancellation exists and build on it (the Cancel button did). The API contract advertises a state machine the server doesn't implement.

## Root cause
Status enum designed up front with aspirational members.

## Proposed fix (specification)
Decide once; both options specified, recommendation first:
**A (recommended): implement real cancellation** — it's cheap with the current task model and the UI already wants it:
1. Keep a `dict[str, asyncio.Task]` keyed by evaluation_id alongside `_background_tasks` (`api/v1/evaluations.py:36`).
2. `POST /evaluations/{id}/cancel`: 409 unless status `running`; `task.cancel()`; on `asyncio.CancelledError` in the runner's outer handler set `status="cancelled"` + broadcast (one site post-ARCH-001).
3. FE Cancel button calls it (fixes FE-002); existing terminal-status handling becomes live code.
**B: delete the fiction** — remove the enum member, the five FE branches, and re-label the Cancel button per FE-002's option B.

## Alternatives considered
Covered: A vs B above. Keeping the phantom member is the only rejected option.

## Verification
A: integration test — start slow eval (patched model latency), cancel, status becomes `cancelled`, no further Results written, WS status event received. B: grep shows no `cancelled` anywhere; FE tests updated.

## Relationship notes
- `related: FE-002` — the Cancel button is the user-facing face of this issue; FE-002 closes via whichever option lands here.
- `related: CONS-002` — enum codification should reflect this decision (do API-004 first).
