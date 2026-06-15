---
id: BUG-002
title: MCP servers are respawned on every user message and previous processes are orphaned
category: bugs
severity: high
effort: S
confidence: high
breaking: false
status: open
depends_on: []
blocks: []
supersedes: []
superseded_by: []
conflicts_with: []
related: [ARCH-007]
child_of: null
affected_paths:
  - backend/app/services/agent_chat_service.py
  - backend/app/mcp/manager.py
---

## Problem
`process_user_message` calls `manager.start_servers(tool_server_ids)` for the session's manager on **every** user message. `start_servers` spawns fresh MCP subprocesses and overwrites `self._clients[server_id]` without stopping the existing client — so each message in a tool-enabled session leaks the previous round's MCP server processes until the session is cleaned up (and the leaked ones are never stopped even then, because the manager no longer references them).

## Evidence
- Per-message call: `backend/app/services/agent_chat_service.py:101-114` (step "4. Set up MCP servers if configured" inside the message handler, not session setup).
- Overwrite without stop: `backend/app/mcp/manager.py:62-90` — `start_servers` resets tool maps (`:62-64`) and on success does `self._clients[server_id] = client` (`:90`) with no `await old.stop()`; `stop_all` (`:159-169`) iterates only current `_clients`.
- Subprocesses are real OS processes: `mcp/client.py:184-191` (`create_subprocess_exec`).

## Impact
A 10-message chat with one MCP server spawns 10 server processes; 9 are orphaned (running, pipes open, never terminated until backend exit via the atexit handler — which also only sees the last one, `manager.py:202-209`). Memory/process leak plus slow first-token latency on every message (handshake + tools/list each time).

## Root cause
Server startup was placed in the message handler instead of session connect, and `start_servers` was written assuming it runs once.

## Proposed fix (specification)
1. Make `start_servers` idempotent per server: in `McpServerManager.start_servers`, if `server_id in self._clients`, reuse the existing client (re-list tools only if the profile changed; simplest: reuse client + cached tool defs). Stop-and-replace only when the profile's command/args/env differ.
2. Rebuild `self._tool_to_server`/`self._openai_tools` from cached definitions instead of resetting and re-handshaking.
3. Optional hardening (cheap): in the overwrite path, `await old_client.stop()` before replacement so a future re-start can't orphan.
4. Leave the call site in `process_user_message` (it doubles as lazy init for the first message); with idempotency it becomes a no-op for later messages.

## Alternatives considered
Move startup to WS connect (`websocket/chat.py`) — cleaner lifecycle but requires agent_config access there and changes failure-surfacing (connect-time vs message-time errors). Idempotent manager is smaller and fixes the leak.

## Verification
- Unit (`tests/unit/test_mcp_manager.py`): call `start_servers(["s1"])` twice with a stubbed client class; assert exactly one client instance constructed and one `start()` call.
- Manual: tool-enabled chat, send 3 messages, `pgrep -f <server cmd> | wc -l` stays 1.

## Relationship notes
- `related: ARCH-007` — the decomposition relocates this call into the extracted setup step; fix the leak first (point fix is independent of the decomposition).
