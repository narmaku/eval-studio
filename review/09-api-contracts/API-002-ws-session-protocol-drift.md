---
id: API-002
title: WS session protocol drift symptoms — missing message_id, phantom score/status types, unhandled connected/session_ended
category: api-contracts
severity: medium
effort: S
confidence: high
breaking: true
status: open
depends_on: [ARCH-003]
blocks: []
supersedes: []
superseded_by: []
conflicts_with: []
related: [FE-006]
child_of: ARCH-003
affected_paths:
  - frontend/src/types/session.ts
  - frontend/src/stores/sessionStore.ts
  - backend/app/services/agent_chat_service.py
  - backend/app/websocket/chat.py
---

## Problem
Concrete catalog of FE↔BE WS chat mismatches (the structural fix is ARCH-003):
1. FE expects `data.message_id` on `message_chunk`/`message_complete`; backend sends neither → FE message ids become `undefined`.
2. FE declares and handles `score`/`status` envelope types the backend never emits — dead branches.
3. Backend emits `connected` and `session_ended`; FE neither types nor handles them (`session_ended` silently dropped; FE relies on its own REST call to learn the session ended).
4. FE `SessionStatus` union contains `'failed'`; the backend never assigns a session status `failed` (statuses set: active/ended/scoring/completed — `sessions.py`, `agent_chat_service.py`).

## Evidence
1. `frontend/src/types/session.ts:109-117` + `stores/sessionStore.ts:237,254` vs `backend/app/services/agent_chat_service.py:190-196,396-405`.
2. `types/session.ts:91-99,124-132`; `sessionStore.ts:329-346`; `grep -rn '"type": "score"\|"type": "status"' backend/app` → none.
3. `backend/app/websocket/chat.py:86-94,194-202`; FE switch `sessionStore.ts:221-361` lacks both cases.
4. `types/session.ts:5` vs backend status assignments (`api/v1/sessions.py:155,236,269`; `agent_chat_service.py:567`; `websocket/chat.py:141`).

## Impact
See ARCH-003; this issue exists as the per-symptom checklist so the fix can be verified item by item.

## Root cause
Hand-mirrored protocol (ARCH-003).

## Proposed fix (specification)
Implemented by ARCH-003 steps 2 & 4 (message_id generation; FE union rewrite; add `connected`/`session_ended` handling; delete `score`/`status` branches). Item 4 additionally: remove `'failed'` from the FE `SessionStatus` union (or, if a failed state is wanted, introduce it backend-first — record choice in ARCH-003's PR).

## Alternatives considered
N/A — checklist record.

## Verification
Each numbered item has a matching assertion in ARCH-003's verification plan; this issue closes when all four pass.

## Relationship notes
- `depends_on: ARCH-003` / `child_of: ARCH-003` — symptoms fixed by the protocol-ownership change; kept separate per the one-issue-one-concern rule because item 4 (status enum truth) outlives the envelope refactor.
- `related: FE-006` — the user-visible rendering consequence of item 1.
