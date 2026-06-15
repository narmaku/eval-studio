---
id: FE-001
title: Evaluations are started via the rerun endpoint plus a 200ms sleep to win a race with the WebSocket
category: frontend
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
related: [PERF-002, ARCH-001]
child_of: null
affected_paths:
  - frontend/src/stores/evaluationStore.ts
  - backend/app/api/v1/evaluations.py
  - backend/app/websocket/progress.py
---

## Problem
`createAndRunEvaluation` creates the evaluation, connects the progress WS, sleeps 200 ms "to let WebSocket connect", then starts the run by calling **`/rerun`** (semantically "re-run", used here because it behaves like run). Two defects: (a) the sleep is a race-condition workaround, not a fix — on a slow connection the first log lines are still lost because the server buffers nothing; (b) the FE never uses the actual `POST /{id}/run` endpoint, so "run" exists only for the SDK/tests while the UI exercises a different code path (which also deletes results — harmless on a fresh eval, but semantically wrong).

## Evidence
- `frontend/src/stores/evaluationStore.ts:111-121`: comments "Connect WebSocket BEFORE triggering", `await new Promise((resolve) => setTimeout(resolve, 200))`, then `api.rerunEvaluation(evaluation.id)`.
- `api.ts` has no `runEvaluation` method (`grep -n "run" frontend/src/services/api.ts` → only rerun).
- No server-side log buffer/replay: `backend/app/websocket/progress.py:12-13` (connections only; no history).

## Impact
Early log lines (model/judge resolution — exactly the lines that explain misconfigurations) are lost nondeterministically; the run/rerun semantic blur means backend changes to rerun (e.g. BUG-015's artifact cleanup) silently alter the *first-run* path too.

## Root cause
No log replay on the server, patched around on the client; `/run` only accepts `pending|failed` while the FE flow at one point hit other statuses, so `rerun` "just worked".

## Proposed fix (specification)
1. Backend: buffer the last N (≈100) log/progress/status messages per evaluation in `websocket/progress.py` (dict[evaluation_id, deque]), replay them on connect in `progress_websocket` before entering the receive loop; expire the buffer when status goes terminal + grace period (or LRU-cap the dict at ~50 evaluations).
2. FE: add `api.runEvaluation` (`POST /{id}/run`); `createAndRunEvaluation` becomes create → run → connect WS (order no longer matters); DELETE the sleep and the comment block (`evaluationStore.ts:111-121`).
3. Keep `/rerun` strictly for the re-run UI affordance.

## Alternatives considered
Return early logs in the run response — rejected: doesn't help mid-run reconnects, which the replay buffer also fixes (reconnecting clients currently lose all history too).

## Verification
- Backend unit: connect a WS after 5 broadcasts → receives the 5 buffered messages in order (extend `tests/unit/test_websocket_progress.py`).
- FE: store test asserting no `setTimeout` in the flow; manual: start an eval with DevTools throttling — resolution log lines always visible.

## Relationship notes
- `related: ARCH-001` — broadcast call sites move; the buffer lives in progress.py and is unaffected; no ordering constraint.
- `related: PERF-002` — same store; independent concerns (buffer growth there is client-side).
