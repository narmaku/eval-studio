---
id: FE-003
title: endSession fires both the WS end_session frame and the REST end call, racing each other
category: frontend
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
related: [ARCH-006, BUG-008]
child_of: null
affected_paths:
  - frontend/src/stores/sessionStore.ts
---

## Problem
`endSession` sends the WS `end_session` frame and then immediately calls REST `POST /sessions/{id}/end`. If the WS path wins (it usually does — same event loop turn server-side), the session is already `ended` when the REST call arrives, which raises 409 Conflict → the store sets an error and re-throws, showing a failure for an end that succeeded.

## Evidence
- `frontend/src/stores/sessionStore.ts:106-122` — both calls back-to-back (`:112-115`).
- WS handler ends the session server-side: `backend/app/websocket/chat.py:188-204` → `end_session` service.
- REST 409 on non-active: `backend/app/api/v1/sessions.py:152-153`.

## Impact
Intermittent spurious "Failed to end session" errors; double work; ordering-dependent behavior differences (REST path's missing cleanup, BUG-008, applies only when REST wins).

## Root cause
Belt-and-suspenders ending added when one path seemed unreliable.

## Proposed fix (specification)
Use exactly one path. Recommended: REST only (works regardless of WS connectivity, which is the failure mode that motivated the duplication):
1. Delete the WS send block (`sessionStore.ts:112-114`).
2. Keep `disconnectWebSocket()` after the REST call resolves (server's WS cleanup handler tolerates the close; `chat.py:124-152`).
3. Precondition: ARCH-006 (REST path gains MCP cleanup) — otherwise removing the WS path reintroduces BUG-008's leak as the *only* behavior.

## Alternatives considered
WS-only — rejected: can't end a session whose socket already dropped (common after laptop sleep), which is exactly when users click End.

## Verification
`sessionStore.test.ts`: endSession issues one network effect; manual: end an active chat — no error toast, session shows ended, MCP gone (post-ARCH-006).

## Relationship notes
- `related: ARCH-006` — practically a dependency for the recommended variant (see step 3); left as `related` because option WS-only wouldn't need it. ROADMAP sequences ARCH-006 first.
- `related: BUG-008` — the REST-path defect that made WS-first attractive.
