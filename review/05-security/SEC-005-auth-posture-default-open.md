---
id: SEC-005
title: Auth is off by default, the FE has no auth support, and dev servers bind 0.0.0.0 — posture is undeclared
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
related: [SEC-002, SEC-004, INFRA-001]
child_of: null
affected_paths:
  - backend/app/core/config.py
  - frontend/src/services/api.ts
  - Makefile
  - dev.sh
  - docker-compose.yml
  - docs/docs/api-reference.md
---

## Problem
The security posture is internally contradictory: `AUTH_DISABLED=true` is the default; the entire frontend never sends an `Authorization` header (so enabling auth bricks the UI); dev launchers and compose bind `0.0.0.0` (LAN-exposed); the API docs claim all endpoints require keys; and the API-key subsystem (hashing, bootstrap mode, last-active-key protection) is fully built but effectively unusable end-to-end. Nobody reading the repo can tell what the intended deployment trust boundary is.

## Evidence
- Default off: `backend/app/core/config.py:27` (`auth_disabled: bool = True`), warning at startup `main.py:64-65`.
- FE sends no auth header anywhere: `frontend/src/services/api.ts:55-63` (headers contain only Content-Type; no token plumbing in the whole `src/`).
- LAN binding: `Makefile:20` and `dev.sh:34,40` (`--host 0.0.0.0`), `docker-compose.yml:10-11` (port published).
- Docs contradiction: `docs/docs/api-reference.md:15-17` ("All endpoints except /api/v1/health require a valid API key") — false twice over (default-off; WS never checks, SEC-002).
- Built-but-stranded subsystem: `backend/app/core/security.py`, `api/v1/api_keys.py`, `tests/integration/test_auth.py`.

## Impact
Anyone on the same network as a dev instance has full control (including the SSRF surface, SEC-004, and agent tool execution). Conversely, a security-conscious user who sets `AUTH_DISABLED=false` discovers the bundled UI stops working — so nobody enables it, and the auth code is dead weight in practice.

## Root cause
Backend auth was built to completion; the FE half and the deployment story never followed.

## Proposed fix (specification)
Decide and implement one coherent posture. Recommended for this product stage:
1. **Declare**: single-trust-domain local tool (SEC-004 step 1). Keep `AUTH_DISABLED=true` default.
2. **Bind localhost by default in dev**: `--host 127.0.0.1` in `Makefile:20` and `dev.sh` (`HOST=0.0.0.0 dev.sh` opt-out documented); compose stays published (containers need it) but document the exposure in README.
3. **Make auth usable or remove FE blocking**: minimal FE support — a settings field storing an API key in localStorage, attached as `Authorization: Bearer` in `request()` (`api.ts:55-63`) and as `?token=` for WS (SEC-002 step 4). This makes `AUTH_DISABLED=false` actually deployable with the bundled UI.
4. **Fix the docs** (`api-reference.md` auth section) to describe the real default and how to enable auth.

## Alternatives considered
Delete the API-key subsystem entirely (pure local tool) — coherent and simpler, but it's the only path to safe shared deployments and is already built/tested; making it usable is ~50 FE lines. If the team prefers deletion, SEC-002 also collapses; record in ROADMAP.

## Verification
- With auth enabled: UI works end-to-end after entering a key (create dataset, run eval, watch progress WS).
- `make dev` binds 127.0.0.1 (`ss -tlnp | grep 8000`).
- Docs match behavior.

## Relationship notes
- `related: SEC-002` — WS auth is the missing backend half of "auth on means auth everywhere".
- `related: SEC-004` — posture statement shared between the two.
- `related: INFRA-001` — production serving topology determines where the UI gets its key setting; no hard ordering.
