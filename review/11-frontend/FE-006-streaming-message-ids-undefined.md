---
id: FE-006
title: Chat messages get id "streaming-undefined"/undefined because the expected message_id never arrives
category: frontend
severity: medium
effort: XS
confidence: high
breaking: false
status: open
depends_on: []
blocks: []
supersedes: []
superseded_by: [ARCH-003]
conflicts_with: []
related: [API-002]
child_of: ARCH-003
affected_paths:
  - frontend/src/stores/sessionStore.ts
---

## Problem
The chunk handler builds message ids from `chunk.data.message_id`, which the backend never sends; every streaming message is `streaming-undefined` and every finalized assistant message gets `id: undefined`. Deduplication and the `findIndex` finalize-matching work today only by accident (there is at most one streaming message at a time), and React list keys degrade to identical/undefined values.

## Evidence
- `frontend/src/stores/sessionStore.ts:237` (`id: \`streaming-${chunk.data.message_id}\``), `:254-258` (`findIndex` on the same id; final `id: complete.data.message_id` → `undefined`).
- Backend payloads lack the field: `backend/app/services/agent_chat_service.py:190-196, 396-405`.

## Impact
Two assistant messages can share `id: undefined` (key collisions → React reconciliation glitches on history-heavy sessions); any future feature keyed on message id (edit, copy-link, scoring per message) is built on sand.

## Root cause
FE written against the aspirational protocol (ARCH-003).

## Proposed fix (specification)
Fixed at the source by ARCH-003 step 2 (backend generates `message_id` per assistant turn). Defensive interim (only if ARCH-003 is delayed): generate a client-side id when missing — `const mid = chunk.data.message_id ?? \`local-${generateId()}\`` held in a ref for the current stream.

## Alternatives considered
N/A — symptom record.

## Verification
Covered by ARCH-003's FE tests (chunks accumulate under one defined id; complete reuses it).

## Relationship notes
- `superseded_by: ARCH-003` / `child_of: ARCH-003` — fully resolved there; `related: API-002` is the protocol-level catalog containing this as item 1.
