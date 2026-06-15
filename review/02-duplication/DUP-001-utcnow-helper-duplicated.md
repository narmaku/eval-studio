---
id: DUP-001
title: _utcnow()/_iso_now() time helpers re-defined in eight modules
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
related: [DATA-003]
child_of: null
affected_paths:
  - backend/app/core/database.py
  - backend/app/models/evaluation.py
  - backend/app/models/dataset.py
  - backend/app/models/session.py
  - backend/app/models/provider.py
  - backend/app/models/rubric.py
  - backend/app/models/environment.py
  - backend/app/services/agent_chat_service.py
  - backend/app/websocket/chat.py
---

## Problem
The identical two-line helper `def _utcnow() -> datetime: return datetime.now(UTC)` is defined seven times, and `def _iso_now() -> str: return datetime.now(UTC).isoformat()` twice more.

## Evidence
`_utcnow`: `core/database.py:27-28`, `models/evaluation.py:9-10`, `models/dataset.py:9-10`, `models/session.py:9-10`, `models/provider.py:11-12`, `models/rubric.py:11-12`, `models/environment.py:9-10`. `_iso_now`: `services/agent_chat_service.py:47-49`, `websocket/chat.py:39-40`.

## Impact
Pure noise plus a hazard: a future timestamp policy change (e.g. DATA-003's timezone fix) must touch nine sites or silently diverge.

## Root cause
Copy-paste when each model file was created; no shared time utility module.

## Proposed fix (specification)
1. Export `utcnow()` and `iso_now()` from `backend/app/core/database.py` (or a new `core/time.py` if preferred — pick one; database.py already hosts `_utcnow` and every model imports from it anyway).
2. Replace all nine local definitions with imports; DELETE the local copies (≈18 lines).

## Alternatives considered
Do nothing — defensible for 18 lines, but DATA-003 makes a single choke point genuinely useful; severity kept low.

## Verification
`grep -rn "def _utcnow\|def _iso_now" backend/app` → no hits; `uv run pytest` green.

## Relationship notes
- `related: DATA-003` — the timezone-aware column fix wants exactly one timestamp helper to change; do this first (it's a 10-minute quick win).
