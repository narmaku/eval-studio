"""Agent chat service — orchestrates interactive LLM chat sessions.

Handles: resolving provider config, calling LLM via litellm (streaming),
parsing tool calls from streamed chunks, executing tool calls via MCP servers,
updating session transcript in DB, and yielding typed JSON envelope messages
for the WebSocket layer.
"""

import json
from collections.abc import AsyncGenerator
from datetime import UTC, datetime

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agent_backends.factory import create_agent_backend
from app.core.exceptions import sanitize_error_for_client
from app.harnesses.factory import create_harness
from app.harnesses.registry import harness_registry
from app.mcp.manager import cleanup_manager, get_or_create_manager
from app.models.evaluation import Evaluation
from app.models.session import Session

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


def _iso_now() -> str:
    """Return current UTC time as ISO 8601 string."""
    return datetime.now(UTC).isoformat()


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

    Yields typed JSON envelope dicts suitable for WebSocket transmission:
    - {"type": "message_chunk", ...}    for each streamed content token
    - {"type": "tool_call", ...}        for each tool call in the response
    - {"type": "tool_executing", ...}   when a tool call begins execution
    - {"type": "tool_result", ...}      when a tool call completes
    - {"type": "message_complete", ...} when the full response is assembled

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
    if session.status != "active":
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

    # 3. Resolve provider from agent_config and create backend adapter (builtin path)
    adapter = create_agent_backend(agent_config)

    # 4. Set up MCP servers if configured
    tool_server_ids = agent_config.get("tool_server_ids", [])
    openai_tools: list[dict] | None = None

    if tool_server_ids:
        manager = get_or_create_manager(session_id)
        openai_tools = await manager.start_servers(tool_server_ids)
        if not openai_tools:
            openai_tools = None  # No tools available, proceed without

        logger.info(
            "agent_chat.tools_loaded",
            session_id=session_id,
            tool_count=len(openai_tools) if openai_tools else 0,
        )

    # 5. Build messages array from transcript + new user message
    transcript = list(session.transcript or [])
    messages_for_llm: list[dict] = []

    # System prompt is passed separately to the adapter
    system_prompt = agent_config.get("system_prompt")
    has_system_in_transcript = any(e.get("role") == "system" for e in transcript)
    if has_system_in_transcript:
        system_prompt = None

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
            messages_for_llm.append(msg)
        elif role == "tool":
            messages_for_llm.append(
                {
                    "role": "tool",
                    "tool_call_id": entry.get("tool_call_id", ""),
                    "content": entry.get("content", ""),
                }
            )
        else:
            messages_for_llm.append({"role": role, "content": entry.get("content", "")})

    # Append the new user message
    user_message = {
        "role": "user",
        "content": content,
        "timestamp": _iso_now(),
    }
    messages_for_llm.append({"role": "user", "content": content})

    # 6. Persist user message to transcript
    transcript.append(user_message)
    session.transcript = transcript
    await db.commit()

    logger.info(
        "agent_chat.llm_call",
        session_id=session_id,
        model=adapter.model,
        message_count=len(messages_for_llm),
    )

    # 7. Agentic loop
    round_count = 0
    all_tool_calls_for_complete: list[dict] = []
    final_content = ""

    while True:
        # Stream the response via adapter
        full_content = ""
        accumulated_tool_calls: dict[int, dict] = {}

        async for chunk in adapter.send_message(messages_for_llm, system_prompt, tools=openai_tools):
            if chunk.done:
                break

            # Content tokens
            if chunk.content:
                full_content += chunk.content
                yield {
                    "type": "message_chunk",
                    "data": {"content": chunk.content},
                    "timestamp": _iso_now(),
                    "sender": "agent",
                    "session_id": session_id,
                }

            # Tool call chunks (accumulated across multiple chunks)
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

        # After first round, don't re-send the system prompt
        system_prompt = None

        # Build tool_calls list
        tool_calls_list = []
        for _idx, tc_data in sorted(accumulated_tool_calls.items()):
            try:
                arguments = json.loads(tc_data["arguments"]) if tc_data["arguments"] else {}
            except json.JSONDecodeError:
                arguments = {"raw": tc_data["arguments"]}

            tc_envelope = {
                "id": tc_data["id"],
                "tool_name": tc_data["name"],
                "arguments": arguments,
                "result": None,
                "duration_ms": None,
                "timestamp": _iso_now(),
                "status": "pending",
            }
            tool_calls_list.append(tc_envelope)

        if tool_calls_list and openai_tools and tool_server_ids:
            # Yield tool_call envelopes (status: pending)
            for tc_envelope in tool_calls_list:
                yield {
                    "type": "tool_call",
                    "data": tc_envelope,
                    "timestamp": _iso_now(),
                    "sender": "agent",
                    "session_id": session_id,
                }

            # Persist assistant message with tool_calls to transcript
            assistant_msg_for_transcript: dict = {
                "role": "assistant",
                "content": full_content,
                "timestamp": _iso_now(),
                "tool_calls": tool_calls_list,
            }
            await db.refresh(session)
            transcript = list(session.transcript or [])
            transcript.append(assistant_msg_for_transcript)
            session.transcript = transcript
            await db.commit()

            # Build assistant message for LLM context (OpenAI format)
            assistant_msg_for_llm: dict = {
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
            messages_for_llm.append(assistant_msg_for_llm)

            # Execute each tool call
            manager = get_or_create_manager(session_id)
            for tc_envelope in tool_calls_list:
                tool_call_id = tc_envelope["id"]
                tool_name = tc_envelope["tool_name"]

                # Yield tool_executing
                yield {
                    "type": "tool_executing",
                    "data": {
                        "tool_call_id": tool_call_id,
                        "tool_name": tool_name,
                    },
                    "timestamp": _iso_now(),
                    "sender": "system",
                    "session_id": session_id,
                }

                # Execute the tool
                try:
                    tool_result = await manager.call_tool(tool_name, tc_envelope["arguments"])
                    result_text = tool_result.result
                    is_error = tool_result.is_error
                    duration_ms = tool_result.duration_ms
                except Exception as exc:
                    logger.exception(
                        "agent_chat.tool_call_error",
                        session_id=session_id,
                        tool_name=tool_name,
                    )
                    result_text = f"Error executing tool: {sanitize_error_for_client(exc)}"
                    is_error = True
                    duration_ms = 0

                # Update the tc_envelope with results
                tc_envelope["result"] = result_text
                tc_envelope["duration_ms"] = duration_ms
                tc_envelope["status"] = "error" if is_error else "completed"

                # Yield tool_result
                yield {
                    "type": "tool_result",
                    "data": {
                        "tool_call_id": tool_call_id,
                        "tool_name": tool_name,
                        "result": result_text,
                        "is_error": is_error,
                        "duration_ms": duration_ms,
                    },
                    "timestamp": _iso_now(),
                    "sender": "system",
                    "session_id": session_id,
                }

                # Add tool result message for LLM context
                messages_for_llm.append(
                    {
                        "role": "tool",
                        "tool_call_id": tool_call_id,
                        "content": result_text,
                    }
                )

                # Persist tool result to transcript
                await db.refresh(session)
                transcript = list(session.transcript or [])
                transcript.append(
                    {
                        "role": "tool",
                        "tool_call_id": tool_call_id,
                        "tool_name": tool_name,
                        "content": result_text,
                        "is_error": is_error,
                        "duration_ms": duration_ms,
                        "timestamp": _iso_now(),
                    }
                )
                session.transcript = transcript
                await db.commit()

            all_tool_calls_for_complete.extend(tool_calls_list)

            # Check max rounds
            round_count += 1
            if round_count >= MAX_TOOL_ROUNDS:
                logger.warning(
                    "agent_chat.max_rounds_reached",
                    session_id=session_id,
                    max_rounds=MAX_TOOL_ROUNDS,
                )
                # Yield message_complete with whatever we have
                final_content = full_content
                break

            # Continue loop — let LLM process the tool results
            continue

        else:
            # No tool calls — text-only response, break the loop
            final_content = full_content

            # Also yield any tool_call envelopes if present but no MCP servers configured
            if tool_calls_list:
                for tc_envelope in tool_calls_list:
                    yield {
                        "type": "tool_call",
                        "data": tc_envelope,
                        "timestamp": _iso_now(),
                        "sender": "agent",
                        "session_id": session_id,
                    }
                all_tool_calls_for_complete.extend(tool_calls_list)

            break

    # 8. Yield message_complete
    yield {
        "type": "message_complete",
        "data": {
            "content": final_content,
            "tool_calls": all_tool_calls_for_complete,
        },
        "timestamp": _iso_now(),
        "sender": "agent",
        "session_id": session_id,
    }

    # 9. Persist final assistant message to transcript (only if we broke out with text)
    if not (tool_calls_list and openai_tools and tool_server_ids):
        # The last response was text-only, persist it
        assistant_message: dict = {
            "role": "assistant",
            "content": final_content,
            "timestamp": _iso_now(),
        }
        if all_tool_calls_for_complete:
            assistant_message["tool_calls"] = all_tool_calls_for_complete

        await db.refresh(session)
        transcript = list(session.transcript or [])
        transcript.append(assistant_message)
        session.transcript = transcript
        await db.commit()

    logger.info(
        "agent_chat.message_complete",
        session_id=session_id,
        content_length=len(final_content),
        tool_call_count=len(all_tool_calls_for_complete),
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

    try:
        all_tool_calls: list[dict] = []
        async for event in harness.send_message(content, history):
            if event.type == "message_chunk":
                yield {
                    "type": "message_chunk",
                    "data": {"content": event.data.get("content", "")},
                    "timestamp": _iso_now(),
                    "sender": "agent",
                    "session_id": session_id,
                }
            elif event.type == "tool_call":
                all_tool_calls.append(event.data)
                yield {
                    "type": "tool_call",
                    "data": event.data,
                    "timestamp": _iso_now(),
                    "sender": "agent",
                    "session_id": session_id,
                }
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
                yield {
                    "type": "message_complete",
                    "data": {
                        "content": final_content,
                        "tool_calls": all_tool_calls,
                    },
                    "timestamp": _iso_now(),
                    "sender": "agent",
                    "session_id": session_id,
                }

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
    if session.status != "active":
        return {
            "status": session.status,
            "ended_at": session.ended_at.isoformat() if session.ended_at else None,
        }

    session.status = "ended"
    session.ended_at = datetime.now(UTC)

    # Update linked Evaluation status to "completed"
    if session.evaluation_id:
        eval_result = await db.execute(select(Evaluation).where(Evaluation.id == session.evaluation_id))
        evaluation = eval_result.scalar_one_or_none()
        if evaluation:
            evaluation.status = "completed"

    await db.commit()

    return {
        "status": session.status,
        "ended_at": session.ended_at.isoformat() if session.ended_at else None,
    }
