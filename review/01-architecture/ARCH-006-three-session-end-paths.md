---
id: ARCH-006
title: Session termination has three divergent implementations
category: architecture
severity: high
effort: S
confidence: high
breaking: false
status: open
depends_on: []
blocks: []
supersedes: [BUG-008]
superseded_by: []
conflicts_with: []
related: [FE-003, ARCH-007]
child_of: null
affected_paths:
  - backend/app/api/v1/sessions.py
  - backend/app/services/agent_chat_service.py
  - backend/app/websocket/chat.py
---

## Problem
Ending a session is implemented three times with different behavior: the REST endpoint neither cleans up MCP servers nor completes the linked evaluation; the service function does both; the WS disconnect handler re-implements both inline with slightly different evaluation-status logic. The REST path therefore leaks MCP subprocess servers, and the three paths disagree about the linked evaluation's final status.

## Evidence
- REST `/sessions/{id}/end` (`backend/app/api/v1/sessions.py:144-162`): sets `status="ended"`, `ended_at`; **no `cleanup_manager` call, no evaluation update**.
- Service `end_session` (`backend/app/services/agent_chat_service.py:535-582`): `cleanup_manager` + sets linked evaluation `status="completed"` unconditionally.
- WS finally-block (`backend/app/websocket/chat.py:124-152`): own copy — `cleanup_manager`, sets session ended, sets evaluation completed *only if it was "running"*.
- MCP managers are per-session subprocess holders (`backend/app/mcp/manager.py:173-199`), so the REST path leaves real OS processes running until WS disconnect or process exit.

## Impact
MCP server subprocesses leak when sessions are ended via REST (the FE calls REST `endSession` in `sessionStore.ts:106-122`, so this is the common path when the WS already dropped). Evaluation status outcomes depend on which path won. Any change to end semantics must be made three times.

## Root cause
The WS handler and REST endpoint were written independently of the service function; no single owner of the transition.

## Proposed fix (specification)
1. Make `agent_chat_service.end_session(session_id, db)` the only implementation. Adjust it to the WS handler's stricter rule: linked evaluation → `completed` only when its status is `running` (keep idempotent early-return for non-active sessions, already present at `:561-565`).
2. REST endpoint (`api/v1/sessions.py:144-162`): replace its body with a call to the service; map `ValueError` → `NotFoundException`; keep the 409 for non-active sessions by checking the service's returned status... — simpler: have the endpoint fetch+validate (404/409) then call the service. DELETE the inline mutation lines.
3. WS finally-block (`websocket/chat.py:135-150`): replace the inline session/evaluation mutation with a call to `end_session(...)` inside the existing try/except; keep `cleanup_manager` inside the service only (delete the separate call at `:131`).
4. Net effect: one transition function, MCP cleanup on every path.

## Alternatives considered
1. Point-fix the REST endpoint (add `cleanup_manager`) — rejected: leaves three copies; the next semantic change re-diverges.
2. Move end-handling into a Session model method — rejected: needs MCP manager + evaluation access; service is the right home.

## Verification
- Extend `tests/integration/test_sessions_api.py`: REST end on a session with a fake registered manager → assert `cleanup_manager` invoked (monkeypatch `_session_managers`) and linked running evaluation becomes `completed`, non-running evaluation untouched.
- Existing WS test `tests/integration/test_agent_chat_ws.py` stays green.

## Relationship notes
- `supersedes: BUG-008` — BUG-008 records the REST-path MCP leak + status divergence; this consolidation removes the entire class, so BUG-008 closes with it (a standalone BUG-008 point-fix would itself be made obsolete by this change, hence supersession rather than dependency).
- `related: FE-003` — the FE double-end (WS + REST) race remains a separate client-side fix; after this issue both paths at least behave identically.
- `related: ARCH-007` — touches the same service file; no ordering constraint.
