---
id: ARCH-007
title: process_user_message is a 380-line generator owning six concerns
category: architecture
severity: medium
effort: M
confidence: high
breaking: false
status: open
depends_on: []
blocks: []
supersedes: []
superseded_by: []
conflicts_with: []
related: [ARCH-003, ARCH-006, BUG-002, DUP-001]
child_of: null
affected_paths:
  - backend/app/services/agent_chat_service.py
---

## Problem
`process_user_message` (`agent_chat_service.py:52-430`) is a single async generator that handles: session loading/validation, harness dispatch, backend adapter construction, MCP server startup, transcript→LLM message mapping, the streaming agentic loop with tool-call accumulation, tool execution, five separate transcript-persist blocks, and envelope construction for seven message types. The transcript-append-commit ritual (`db.refresh; transcript = list(...); append; assign; commit`) is repeated five times within the file.

## Evidence
- Function span: `backend/app/services/agent_chat_service.py:52-430` (379 lines); subprocess variant `_subprocess_process` repeats envelope mapping `:433-532`.
- Transcript persist ritual ×5: `:161-164`, `:256-260`, `:344-358`, `:418-422`, `:454-455`.
- Inline envelope dicts ≥10 sites (see ARCH-003 evidence).
- Step-9 persistence condition re-derives loop state: `if not (tool_calls_list and openai_tools and tool_server_ids):` (`:408`) — correctness depends on variables left over from the final loop iteration.

## Impact
The most complex behavior in the product (agentic loop) is effectively untestable in units smaller than "the whole conversation"; subtle state bugs (like the step-9 condition and the per-message MCP restart, BUG-002) hide in plain sight; envelope changes (ARCH-003) require edits sprinkled across 400 lines.

## Root cause
Incremental feature growth (tools, harnesses, multi-round loop) inside one function; no extraction pressure because only the WS handler calls it.

## Proposed fix (specification)
Decompose within the same module (no new abstraction layer):
1. `async def _append_to_transcript(db, session, entry: dict) -> None` — single copy of the refresh/copy/append/commit ritual (5 call sites).
2. `def _transcript_to_llm_messages(transcript: list[dict]) -> list[dict]` — pure function from `:126-151` (unit-testable).
3. `async def _stream_one_round(adapter, messages, system_prompt, tools) -> tuple[str, list[ToolCallEnvelope]]` — the streaming + tool-chunk accumulation from `:178-236`.
4. `async def _execute_tool_calls(manager, tool_calls, messages, session, db) -> AsyncGenerator[dict]` — execution + result envelopes + persistence from `:280-360`.
5. `process_user_message` becomes the ~60-line conductor: validate → harness dispatch → setup → loop {stream round; if no tools: break; execute} → complete envelope → persist final message. Replace the `:408` condition with an explicit `final_message_persisted: bool` flag set where persistence happens.
6. Envelope construction goes through the typed models from ARCH-003 if that lands first; otherwise a local `_envelope(type_, data, sender)` helper.

## Alternatives considered
1. Promote the harness abstraction so the builtin loop is "just another harness" — appealing symmetry, rejected for now: SIMP-003 deletes the dead BuiltinHarness instead; revisit only if a second builtin-style backend appears.
2. Leave as is with more tests — rejected: the function's seams are exactly what tests need and currently lack.

## Verification
- New unit tests for `_transcript_to_llm_messages` (system-prompt suppression, tool-call mapping, `_serialize_tool_arguments` interplay) and `_stream_one_round` (chunk accumulation by index).
- Existing `tests/unit/test_agentic_loop.py`, `test_agent_chat_service.py`, `tests/integration/test_agent_chat_ws.py` stay green.

## Relationship notes
- `related: ARCH-003` — envelope typing; either order, but doing ARCH-003 first makes step 6 trivial.
- `related: ARCH-006` — same file; `end_session` is untouched by this decomposition.
- `related: BUG-002` — the per-message MCP restart fix (manager reuse) slots into the setup section extracted here; the bug can and should be fixed independently/first.
- `related: DUP-001` — `_iso_now` duplication is resolved by the shared time helper there.
