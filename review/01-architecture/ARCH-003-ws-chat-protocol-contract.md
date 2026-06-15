---
id: ARCH-003
title: Agent-chat WebSocket protocol has no single owner; FE and BE implement different protocols
category: architecture
severity: high
effort: M
confidence: high
breaking: true
status: open
depends_on: []
blocks: [API-002, TEST-003]
supersedes: [FE-006]
superseded_by: []
conflicts_with: []
related: [ARCH-004, ARCH-007]
child_of: null
affected_paths:
  - backend/app/services/agent_chat_service.py
  - backend/app/websocket/chat.py
  - frontend/src/types/session.ts
  - frontend/src/stores/sessionStore.ts
---

## Problem
The chat WS envelope protocol is defined twice — implicitly in backend dict literals and explicitly in frontend TS types — and the two have drifted: the FE expects fields the BE never sends (`message_id`), handles message types the BE never emits (`score`, `status`), and ignores types the BE does emit (`connected`, `session_ended`). There is no schema, no version field, and no single document describing the protocol.

## Evidence
- FE expects `data.message_id` on chunks/completes: `frontend/src/types/session.ts:109-117`; used to build ids at `frontend/src/stores/sessionStore.ts:237,254` — backend sends only `{"content": …}` (`backend/app/services/agent_chat_service.py:190-196`) and `{"content", "tool_calls"}` (`:396-405`), so FE message ids become `"streaming-undefined"` / `undefined`.
- FE `WsMessageType` includes `'score' | 'status'` (`types/session.ts:91-99`); `grep -rn '"type": "score"\|"type": "status"' backend/app/services/agent_chat_service.py backend/app/websocket/chat.py` → no hits.
- BE emits `connected` (`websocket/chat.py:86-94`) and `session_ended` (`:194-202`); neither appears in `WsMessageType` nor in the `handleWsMessage` switch (`sessionStore.ts:221-361`).
- Envelope shape itself is assembled ad hoc ≥10 times in `agent_chat_service.py` (e.g. `:190-196, 240-247, 287-296, 320-332, 396-405, 472-507`).

## Impact
Message identity is broken in the FE today (every assistant message gets id `undefined`; dedupe and React keys silently rely on array position). Dead protocol branches mislead readers on both sides. Any protocol change requires synchronized edits to dict literals scattered across a 580-line generator and a hand-written TS union.

## Root cause
The protocol grew inside the chat loop; the FE types were written aspirationally ("TODO: generate from OpenAPI", `types/session.ts:1-2`) and never reconciled.

## Proposed fix (specification)
Make the backend the protocol owner with typed envelopes; regenerate/align the FE union; delete dead branches.

1. Create `backend/app/schemas/ws_chat.py` with Pydantic models, one per envelope: `ConnectedMsg`, `MessageChunk` (`content: str`, `message_id: str`), `MessageComplete` (`content`, `message_id`, `tool_calls`), `ToolCallMsg`, `ToolExecutingMsg`, `ToolResultMsg`, `SessionEnded`, `ErrorMsg` — all with `type: Literal[...]`, `timestamp`, `sender`, `session_id`.
2. Generate `message_id` (uuid4) once per assistant turn in `process_user_message` and include it in every chunk and the complete envelope (fixes FE-006 at the source).
3. Replace each inline dict in `agent_chat_service.py` / `websocket/chat.py` with `Model(...).model_dump()` via a small `def envelope(model) -> dict` helper.
4. Frontend: rewrite `types/session.ts` WS section to exactly the eight types above; drop `WsScoreMessage`/`WsStatusMessage`; add `connected` (no-op or sets `isConnected`) and `session_ended` (sets session status, stops `isProcessing`) cases in `handleWsMessage`.
5. Breaking change: envelope field additions only (`message_id`); no consumer outside this repo.

## Alternatives considered
1. Full AsyncAPI/JSON-schema codegen for WS — rejected: heavyweight for eight message types in an internal tool; revisit with ARCH-004 if drift recurs.
2. FE-side defensive coding only (fallback ids) — rejected: leaves the contract unowned, drift recurs.

## Verification
- Unit: assert each envelope model serializes with the exact keys the FE switch consumes; extend `tests/unit/test_agentic_loop.py` to assert `message_id` consistency chunk↔complete.
- FE: extend `sessionStore.test.ts` — chunks accumulate under one id; `session_ended` flips status.
- Manual: run an agent chat; verify no `streaming-undefined` ids in React DevTools and no unhandled envelope console paths.

## Relationship notes
- `blocks: API-002` — API-002 catalogs the concrete drift symptoms; it is implemented *by* this issue's steps 2/4 and should be closed when this lands (kept separate because API-002 also covers the session REST status enum).
- `related: ARCH-004` — if OpenAPI type generation is adopted, the Pydantic envelopes from step 1 flow into the generated TS types for free.
- `related: ARCH-007` — decomposing the chat loop makes step 3's envelope replacement mechanical; either order works.
- `supersedes: FE-006` — FE-006 is the user-visible symptom (undefined ids); fully fixed by step 2, closes without separate action.
- `blocks: TEST-003` — its WS protocol-conformance test targets the typed envelopes introduced here.
