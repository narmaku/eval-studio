---
id: DUP-005
title: WebSocket broadcast + dead-connection sweep copied three times in progress.py
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
related: [SEC-002]
child_of: null
affected_paths:
  - backend/app/websocket/progress.py
---

## Problem
`broadcast_progress`, `broadcast_log`, and `broadcast_status` each repeat the same 20-line pattern: snapshot connections under lock, build a message dict, loop `send_json` collecting dead sockets, then sweep them under lock. Only the message payload differs.

## Evidence
`backend/app/websocket/progress.py:31-64` (progress), `:67-99` (log), `:102-127` (status) — the send/sweep halves are character-identical.

## Impact
~40 redundant lines; a fix to the sweep (e.g. logging dropped clients, or bounding send time) must be applied three times.

## Proposed fix (specification)
1. Add `async def _broadcast(evaluation_id: str, message: dict) -> None` containing the snapshot/send/sweep logic once.
2. The three public functions shrink to message-dict construction + `await _broadcast(...)` (keep their signatures — call sites unchanged).
3. Net deletion ≈ 45 lines.

## Root cause
Second and third broadcast types copied from the first.

## Alternatives considered
Do nothing — viable, but this is a 15-minute quick win in a file SEC-002 will touch anyway.

## Verification
`uv run pytest tests/unit/test_websocket_progress.py` green; behavior identical (same JSON payloads).

## Relationship notes
- `related: SEC-002` — WS auth changes touch this file; doing this first makes that diff smaller. No ordering requirement.
