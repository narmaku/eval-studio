---
id: PERF-003
title: Every authenticated request scans all active API keys and commits a last_used_at write
category: performance
severity: trivial
effort: XS
confidence: high
breaking: false
status: open
depends_on: []
blocks: []
supersedes: []
superseded_by: []
conflicts_with: []
related: [SEC-005]
child_of: null
affected_paths:
  - backend/app/core/security.py
---

## Problem
`verify_api_key` loads every active key row and compares each hash with `hmac.compare_digest`; `require_auth` then writes `last_used_at` and commits — one full-table scan plus one write transaction per authenticated request.

## Evidence
`backend/app/core/security.py:67-74` (scan + loop), `:100-104` (per-request commit). The hash column is unique-indexed (`models/api_key.py:13`) and a SHA-256 preimage can't be timing-probed via an index lookup, so the scan buys no real security.

## Impact
Negligible today (auth default-off, keys ≤ handful). Filed because it doubles as a write amplification on SQLite (WAL churn) the moment auth is actually used per SEC-005.

## Root cause
Timing-safety applied one layer too broadly.

## Proposed fix (specification)
1. `select(ApiKey).where(ApiKey.key_hash == token_hash, ApiKey.is_active.is_(True))` → single indexed lookup (keep `hmac.compare_digest(found.key_hash, token_hash)` afterwards if the belt-and-suspenders comparison is desired).
2. Throttle the usage write: update `last_used_at` only if older than 60s (`if api_key.last_used_at is None or now - last > 60`), skipping the commit otherwise.

## Alternatives considered
Do nothing — fine until SEC-005 makes auth real; that's why this is trivial severity but kept on file.

## Verification
`tests/unit/test_security.py` / `tests/integration/test_auth.py` green; add: two requests within a minute produce one `last_used_at` change.

## Relationship notes
- `related: SEC-005` — only matters in the world where SEC-005 makes auth usable; schedule together.
