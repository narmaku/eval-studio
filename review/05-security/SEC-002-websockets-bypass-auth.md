---
id: SEC-002
title: WebSocket endpoints enforce no authentication or origin checks even when API auth is enabled
category: security
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
related: [SEC-005, DUP-005]
child_of: null
affected_paths:
  - backend/app/websocket/progress.py
  - backend/app/websocket/chat.py
  - frontend/src/stores/evaluationStore.ts
  - frontend/src/stores/sessionStore.ts
---

## Problem
When `AUTH_DISABLED=false`, every REST router requires a Bearer key (`dependencies=[Depends(require_auth)]`), but both WS endpoints accept any connection: `/ws/progress/{evaluation_id}` streams evaluation logs (which include question text and model output previews) and `/ws/session/{session_id}` allows **sending messages to an agent with tool access** given only a guessable-ish session UUID. Neither checks `Origin`, so a malicious website can also open these sockets from a victim's browser (classic cross-site WebSocket hijacking — no cookies involved here, but the endpoints are also unauthenticated, so any reachable network peer suffices anyway).

## Evidence
- No auth dependency on WS routers: `backend/app/websocket/progress.py:130-145`, `websocket/chat.py:56-77` (compare `api/v1/evaluations.py:32`).
- Docs claim the opposite: `docs/docs/api-reference.md:15-17` ("All endpoints except /api/v1/health require a valid API key").
- Chat socket performs privileged actions: `_handle_user_message` drives the agent + MCP tools (`chat.py:155-185`).

## Impact
With auth enabled (i.e., precisely the deployments that care), the most sensitive interactive surface is open: anyone who can reach the port and learn/guess a session id can puppet the agent and its tools; progress logs leak evaluation content. Severity is medium not high only because SEC-005's recommended posture is "localhost-only tool" — in any shared-network deployment this is high.

## Root cause
`require_auth` is an HTTP dependency; nobody built the WS equivalent.

## Proposed fix (specification)
1. Add `async def require_ws_auth(websocket: WebSocket) -> None` in `core/security.py`: if `settings.auth_disabled` return; else read the token from the `Authorization` header **or** a `?token=` query param (browsers can't set WS headers; the FE will use the query param), verify via `verify_api_key` with a fresh session, and on failure `await websocket.close(code=4401)` after accept.
2. Call it at the top of both endpoints (after `accept()`, mirroring the existing validate-then-close pattern in `chat.py:64-78`).
3. Origin check: compare the `Origin` header (when present) against `settings.cors_origins_list`; close with 4403 on mismatch. Skip when origin absent (non-browser clients).
4. FE: thread an optional token into `getWsUrl`/`buildWsUrl` (`evaluationStore.ts:52-61`, `sessionStore.ts:22-33`) — only needed once the FE gains auth support at all (today it sends no Authorization header anywhere; see SEC-005).

## Alternatives considered
Ticket-based WS auth (short-lived token minted via REST) — the robust pattern, but overkill until the FE has any auth story; query-param key matches the current threat model.

## Verification
Tests in `tests/integration/test_auth.py`: with `auth_disabled=False`, WS connect without token → closed 4401; with valid `?token=` → connected. Origin mismatch → 4403.

## Relationship notes
- `related: SEC-005` — defines when auth is on at all; this issue makes "auth on" mean something for WS.
- `related: DUP-005` — same file (progress.py); land DUP-005's helper first for a smaller diff.
