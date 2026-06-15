---
id: BUG-008
title: REST POST /sessions/{id}/end leaks MCP servers and skips evaluation completion
category: bugs
severity: medium
effort: XS
confidence: high
breaking: false
status: open
depends_on: []
blocks: []
supersedes: []
superseded_by: [ARCH-006]
conflicts_with: []
related: [FE-003]
child_of: ARCH-006
affected_paths:
  - backend/app/api/v1/sessions.py
---

## Problem
The REST end-session endpoint mutates the session inline and, unlike the other two end paths, never calls `cleanup_manager` (MCP subprocesses keep running) and never completes the linked evaluation (it stays `running` forever in the evaluations list).

## Evidence
`backend/app/api/v1/sessions.py:144-162` — full body: status/ended_at/commit only. Compare `services/agent_chat_service.py:535-582` (cleanup + evaluation update) and `websocket/chat.py:124-152` (both, inline). FE calls this REST endpoint as its primary end path (`frontend/src/stores/sessionStore.ts:115`).

## Impact
Tool-enabled sessions ended from the UI leave MCP server processes alive until the WS disconnect handler happens to run (it may not, if the socket already closed) or backend exit; the linked auto-created evaluation (`sessions.py:77-85`) is stuck `running`, polluting dashboards and blocking deletion (`evaluations.py:282-283` refuses to delete running evaluations).

## Root cause
Three implementations of one transition (ARCH-006).

## Proposed fix (specification)
Symptom record — ARCH-006 routes this endpoint through the single `end_session` service function. Interim point fix if needed: insert `await cleanup_manager(session_id)` and the evaluation-completion block before the commit.

## Alternatives considered
N/A — see ARCH-006.

## Verification
Covered by ARCH-006's integration test (REST end → manager cleaned, running evaluation → completed).

## Relationship notes
- `superseded_by: ARCH-006` / `child_of: ARCH-006` — consolidation removes this divergence entirely.
- `related: FE-003` — the FE's WS+REST double-end makes this endpoint the race loser/winner nondeterministically.
