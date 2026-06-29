"""Agent chat service — orchestrates interactive LLM chat sessions.

Handles: resolving provider config, calling LLM via litellm (streaming),
parsing tool calls from streamed chunks, executing tool calls via MCP servers,
updating session transcript in DB, and yielding typed JSON envelope messages
for the WebSocket layer.
"""

import json
from collections.abc import AsyncGenerator

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agent_backends.factory import create_agent_backend
from app.core.database import iso_now as _iso_now
from app.core.database import utcnow
from app.core.exceptions import sanitize_error_for_client
from app.harnesses.factory import create_harness
from app.harnesses.registry import harness_registry
from app.mcp.manager import cleanup_manager, get_or_create_manager
from app.models.evaluation import Evaluation
from app.models.session import Session
from app.schemas.evaluation import EvaluationStatus
from app.schemas.session import SessionStatus
from app.schemas.ws_chat import (
    MessageChunk,
    MessageChunkData,
    MessageComplete,
    MessageCompleteData,
    ToolCallMsg,
    ToolExecutingData,
    ToolExecutingMsg,
    ToolResultData,
    ToolResultMsg,
    new_message_id,
)

logger = structlog.get_logger()

MAX_TOOL_ROUNDS = 10


def _serialize_tool_arguments(arguments: object) -> str:
    """Serialize tool arguments to JSON string for LLM messages.

    Works around a LiteLLM bug where Gemini's converter crashes on empty
    arguments ('{}') because its loop never creates a FunctionCall object.
    """
    if isinstance(arguments, dict):
        if not arguments:
            return '{"_": ""}'
        return json.dumps(arguments)
    if isinstance(arguments, str):
        if arguments in ("", "{}"):
            return '{"_": ""}'
        return arguments
    return "{}"


async def _append_to_transcript(db: AsyncSession, session: Session, entry: dict) -> None:
    """Persist a single entry to the session transcript (refresh → copy → append → commit)."""
    await db.refresh(session)
    transcript = list(session.transcript or [])
    transcript.append(entry)
    session.transcript = transcript
    await db.commit()


def _transcript_to_llm_messages(transcript: list[dict]) -> list[dict]:
    """Convert stored transcript entries to the OpenAI messages format for LLM calls.

    Handles three entry shapes: assistant with tool_calls, tool results, and
    plain user/system/assistant messages.
    """
    messages: list[dict] = []
    for entry in transcript:
        role = entry["role"]
        if role == "assistant" and entry.get("tool_calls"):
            msg: dict = {"role": "assistant", "content": entry.get("content") or None}
            msg["tool_calls"] = [
                {
                    "id": tc.get("id", ""),
                    "type": "function",
                    "function": {
                        "name": tc.get("tool_name", tc.get("name", "")),
                        "arguments": _serialize_tool_arguments(tc.get("arguments", {})),
                    },
                }
                for tc in entry["tool_calls"]
            ]
            messages.append(msg)
        elif role == "tool":
            messages.append(
                {
                    "role": "tool",
                    "tool_call_id": entry.get("tool_call_id", ""),
                    "content": entry.get("content", ""),
                }
            )
        else:
            messages.append({"role": role, "content": entry.get("content", "")})
    return messages


def _build_tool_calls(accumulated: dict[int, dict]) -> list[dict]:
    """Build tool-call envelope dicts from chunk-accumulated raw tool calls."""
    tool_calls = []
    for _idx, tc_data in sorted(accumulated.items()):
        try:
            arguments = json.loads(tc_data["arguments"]) if tc_data["arguments"] else {}
        except json.JSONDecodeError:
            arguments = {"raw": tc_data["arguments"]}

        tool_calls.append(
            {
                "id": tc_data["id"],
                "tool_name": tc_data["name"],
                "arguments": arguments,
                "result": None,
                "duration_ms": None,
                "timestamp": _iso_now(),
                "status": "pending",
            }
        )
    return tool_calls


async def _execute_tool_calls(
    manager,
    tool_calls: list[dict],
    messages_for_llm: list[dict],
    session: Session,
    db: AsyncSession,
    session_id: str,
) -> AsyncGenerator[dict, None]:
    """Execute tool calls, persist results, and yield WS envelopes.

    For each tool call: yields a tool_executing envelope, runs the tool,
    updates the tool_call envelope in-place with the result, yields a
    tool_result envelope, appends the result to messages_for_llm, and
    persists the tool result to the transcript.
    """
    for tc_envelope in tool_calls:
        tool_call_id = tc_envelope["id"]
        tool_name = tc_envelope["tool_name"]

        yield ToolExecutingMsg(
            data=ToolExecutingData(tool_call_id=tool_call_id, tool_name=tool_name),
            sender="system",
            session_id=session_id,
        ).model_dump()

        try:
            tool_result = await manager.call_tool(tool_name, tc_envelope["arguments"])
            result_text = tool_result.result
            is_error = tool_result.is_error
            duration_ms = tool_result.duration_ms
        except Exception as exc:
            logger.exception("agent_chat.tool_call_error", session_id=session_id, tool_name=tool_name)
            result_text = f"Error executing tool: {sanitize_error_for_client(exc)}"
            is_error = True
            duration_ms = 0

        tc_envelope["result"] = result_text
        tc_envelope["duration_ms"] = duration_ms
        tc_envelope["status"] = "error" if is_error else "completed"

        yield ToolResultMsg(
            data=ToolResultData(
                tool_call_id=tool_call_id,
                tool_name=tool_name,
                result=result_text,
                is_error=is_error,
                duration_ms=duration_ms,
            ),
            sender="system",
            session_id=session_id,
        ).model_dump()

        messages_for_llm.append({"role": "tool", "tool_call_id": tool_call_id, "content": result_text})

        await _append_to_transcript(
            db,
            session,
            {
                "role": "tool",
                "tool_call_id": tool_call_id,
                "tool_name": tool_name,
                "content": result_text,
                "is_error": is_error,
                "duration_ms": duration_ms,
                "timestamp": _iso_now(),
            },
        )


async def process_user_message(
    session_id: str,
    content: str,
    db: AsyncSession,
) -> AsyncGenerator[dict, None]:
    """Process a user message: call LLM, stream response, execute tools, update transcript.

    Implements an agentic loop: if the LLM returns tool_calls, they are executed
    against configured MCP servers and the results are fed back to the LLM.
    The loop continues until the LLM returns text only (no tool_calls) or
    the maximum number of tool rounds is reached.

    Yields typed JSON envelope dicts suitable for WebSocket transmission.

    Args:
        session_id: The session to process the message for.
        content: The user's message text.
        db: Async database session.

    Raises:
        ValueError: If the session is not found or not active.
    """
    # 1. Load and validate session
    result = await db.execute(select(Session).where(Session.id == session_id))
    session = result.scalar_one_or_none()
    if not session:
        raise ValueError(f"Session '{session_id}' not found")
    if session.status != SessionStatus.ACTIVE:
        raise ValueError(f"Session '{session_id}' is not active (status: {session.status})")

    # 2. Check for harness dispatch
    agent_config = session.agent_config or {}
    harness_id = agent_config.get("harness_id")
    if harness_id:
        profile = harness_registry.get_harness(harness_id)
        if profile and profile.type == "subprocess":
            async for envelope in _subprocess_process(session_id, content, db, session, agent_config, harness_id):
                yield envelope
            return

    # 3. Create backend adapter + set up MCP servers
    adapter = create_agent_backend(agent_config)
    tool_server_ids = agent_config.get("tool_server_ids", [])
    openai_tools: list[dict] | None = None

    if tool_server_ids:
        manager = get_or_create_manager(session_id)
        openai_tools = await manager.start_servers(tool_server_ids)
        if not openai_tools:
            openai_tools = None
        logger.info(
            "agent_chat.tools_loaded",
            session_id=session_id,
            tool_count=len(openai_tools) if openai_tools else 0,
        )

    # 4. Build LLM messages from transcript
    transcript = list(session.transcript or [])
    messages_for_llm = _transcript_to_llm_messages(transcript)

    system_prompt = agent_config.get("system_prompt")
    if any(e.get("role") == "system" for e in transcript):
        system_prompt = None

    # 5. Append user message to LLM context and persist
    messages_for_llm.append({"role": "user", "content": content})
    await _append_to_transcript(db, session, {"role": "user", "content": content, "timestamp": _iso_now()})

    logger.info("agent_chat.llm_call", session_id=session_id, model=adapter.model, message_count=len(messages_for_llm))

    # 6. Agentic loop — each round gets its own message_id and message_complete
    round_count = 0
    total_tool_calls = 0

    while True:
        # New message_id for each round
        round_message_id = new_message_id()

        # Stream one round — accumulate content and tool-call chunks
        full_content = ""
        accumulated_tool_calls: dict[int, dict] = {}

        async for chunk in adapter.send_message(messages_for_llm, system_prompt, tools=openai_tools):
            if chunk.done:
                break
            if chunk.content:
                full_content += chunk.content
                yield MessageChunk(
                    data=MessageChunkData(content=chunk.content, message_id=round_message_id),
                    sender="agent",
                    session_id=session_id,
                ).model_dump()
            if chunk.tool_call_chunk:
                tc = chunk.tool_call_chunk
                idx = tc["index"]
                if idx not in accumulated_tool_calls:
                    accumulated_tool_calls[idx] = {
                        "id": tc.get("id", ""),
                        "name": tc.get("name", ""),
                        "arguments": tc.get("arguments", ""),
                    }
                else:
                    if tc.get("id"):
                        accumulated_tool_calls[idx]["id"] = tc["id"]
                    if tc.get("name"):
                        accumulated_tool_calls[idx]["name"] += tc["name"]
                    if tc.get("arguments"):
                        accumulated_tool_calls[idx]["arguments"] += tc["arguments"]

        system_prompt = None
        tool_calls_list = _build_tool_calls(accumulated_tool_calls)

        if tool_calls_list and openai_tools and tool_server_ids:
            for tc_envelope in tool_calls_list:
                yield ToolCallMsg(data=tc_envelope, sender="agent", session_id=session_id).model_dump()

            # Persist assistant message with tool_calls
            await _append_to_transcript(
                db,
                session,
                {"role": "assistant", "content": full_content, "timestamp": _iso_now(), "tool_calls": tool_calls_list},
            )

            # Add assistant message to LLM context (OpenAI format)
            messages_for_llm.append(
                {
                    "role": "assistant",
                    "content": full_content or None,
                    "tool_calls": [
                        {
                            "id": tc["id"],
                            "type": "function",
                            "function": {
                                "name": tc["tool_name"],
                                "arguments": _serialize_tool_arguments(tc["arguments"]),
                            },
                        }
                        for tc in tool_calls_list
                    ],
                }
            )

            # Execute tools — yields tool_executing/tool_result envelopes
            tool_manager = get_or_create_manager(session_id)
            async for envelope in _execute_tool_calls(
                tool_manager, tool_calls_list, messages_for_llm, session, db, session_id
            ):
                yield envelope

            total_tool_calls += len(tool_calls_list)

            round_count += 1
            at_max_rounds = round_count >= MAX_TOOL_ROUNDS

            if at_max_rounds:
                logger.warning("agent_chat.max_rounds_reached", session_id=session_id, max_rounds=MAX_TOOL_ROUNDS)

            # Yield per-round message_complete:
            # - intermediate rounds (not at max): is_final=False, skip if no text content
            # - final round (at max): is_final=True, always emit
            if full_content or at_max_rounds:
                yield MessageComplete(
                    data=MessageCompleteData(
                        content=full_content,
                        message_id=round_message_id,
                        is_final=at_max_rounds,
                        tool_calls=tool_calls_list,
                    ),
                    sender="agent",
                    session_id=session_id,
                ).model_dump()

            if at_max_rounds:
                break
            continue

        else:
            # Final round — text only (or text + unexecutable tool calls)
            if tool_calls_list:
                for tc_envelope in tool_calls_list:
                    yield ToolCallMsg(data=tc_envelope, sender="agent", session_id=session_id).model_dump()

            # Yield final message_complete (is_final=True)
            yield MessageComplete(
                data=MessageCompleteData(
                    content=full_content,
                    message_id=round_message_id,
                    is_final=True,
                    tool_calls=tool_calls_list,
                ),
                sender="agent",
                session_id=session_id,
            ).model_dump()

            # Persist final assistant message
            assistant_entry: dict = {"role": "assistant", "content": full_content, "timestamp": _iso_now()}
            if tool_calls_list:
                assistant_entry["tool_calls"] = tool_calls_list
            await _append_to_transcript(db, session, assistant_entry)
            break

    logger.info(
        "agent_chat.message_complete",
        session_id=session_id,
        content_length=len(full_content),
        tool_call_count=total_tool_calls,
        tool_rounds=round_count,
    )


async def _subprocess_process(
    session_id: str,
    content: str,
    db: AsyncSession,
    session: Session,
    agent_config: dict,
    harness_id: str,
) -> AsyncGenerator[dict, None]:
    """Process a message using a subprocess harness.

    Creates a SubprocessHarness, sends the message, converts HarnessEvents
    to WebSocket envelopes, and persists to the transcript.
    """
    # Persist user message to transcript
    transcript = list(session.transcript or [])
    user_message = {
        "role": "user",
        "content": content,
        "timestamp": _iso_now(),
    }
    transcript.append(user_message)
    session.transcript = transcript
    await db.commit()

    # Build history from transcript
    history = [
        {"role": e.get("role", "user"), "content": e.get("content", "")}
        for e in transcript
        if e.get("role") in ("user", "assistant", "system")
    ]

    # Create and start harness
    harness = create_harness(harness_id)
    await harness.start_session(agent_config)

    sub_message_id = new_message_id()
    try:
        all_tool_calls: list[dict] = []
        async for event in harness.send_message(content, history):
            if event.type == "message_chunk":
                yield MessageChunk(
                    data=MessageChunkData(content=event.data.get("content", ""), message_id=sub_message_id),
                    sender="agent",
                    session_id=session_id,
                ).model_dump()
            elif event.type == "tool_call":
                all_tool_calls.append(event.data)
                yield ToolCallMsg(
                    data=event.data,
                    sender="agent",
                    session_id=session_id,
                ).model_dump()
            elif event.type == "tool_result":
                yield {
                    "type": "tool_result",
                    "data": event.data,
                    "timestamp": _iso_now(),
                    "sender": "system",
                    "session_id": session_id,
                }
            elif event.type == "message_complete":
                final_content = event.data.get("content", "")
                yield MessageComplete(
                    data=MessageCompleteData(
                        content=final_content,
                        message_id=sub_message_id,
                        is_final=True,
                        tool_calls=all_tool_calls,
                    ),
                    sender="agent",
                    session_id=session_id,
                ).model_dump()

                # Persist assistant message to transcript
                assistant_message: dict = {
                    "role": "assistant",
                    "content": final_content,
                    "timestamp": _iso_now(),
                }
                if all_tool_calls:
                    assistant_message["tool_calls"] = all_tool_calls

                await db.refresh(session)
                transcript = list(session.transcript or [])
                transcript.append(assistant_message)
                session.transcript = transcript
                await db.commit()
            elif event.type == "error":
                yield {
                    "type": "error",
                    "data": {"message": event.data.get("message", "Unknown error")},
                    "timestamp": _iso_now(),
                    "sender": "system",
                    "session_id": session_id,
                }
    finally:
        await harness.stop_session()


async def end_session(session_id: str, db: AsyncSession) -> dict:
    """End a session and clean up resources. Does NOT score.

    Scoring is a separate explicit step via the POST /sessions/{id}/score endpoint.

    Also cleans up any MCP server managers associated with the session.

    Args:
        session_id: The session to end.
        db: Async database session.

    Returns:
        Dict with session status and ended_at.

    Raises:
        ValueError: If session not found.
    """
    # Clean up MCP managers
    await cleanup_manager(session_id)

    result = await db.execute(select(Session).where(Session.id == session_id))
    session = result.scalar_one_or_none()
    if not session:
        raise ValueError(f"Session '{session_id}' not found")

    # Idempotency guard: if the session is already ended, return current state
    if session.status != SessionStatus.ACTIVE:
        return {
            "status": session.status,
            "ended_at": session.ended_at.isoformat() if session.ended_at else None,
        }

    session.status = SessionStatus.ENDED
    session.ended_at = utcnow()

    # Update linked Evaluation: only transition to "completed" when currently "running"
    if session.evaluation_id:
        eval_result = await db.execute(select(Evaluation).where(Evaluation.id == session.evaluation_id))
        evaluation = eval_result.scalar_one_or_none()
        if evaluation and evaluation.status == EvaluationStatus.RUNNING:
            evaluation.status = EvaluationStatus.COMPLETED

    await db.commit()

    return {
        "status": session.status,
        "ended_at": session.ended_at.isoformat() if session.ended_at else None,
    }
