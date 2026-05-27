"""Agent chat service — orchestrates interactive LLM chat sessions.

Handles: resolving provider config, calling LLM via litellm (streaming),
parsing tool calls from streamed chunks, updating session transcript in DB,
and yielding typed JSON envelope messages for the WebSocket layer.
"""

import json
from collections.abc import AsyncGenerator
from datetime import UTC, datetime

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.base import JudgeConfigParams, Message, ToolCall
from app.adapters.factory import create_evaluation_adapter
from app.agent_backends.factory import create_agent_backend
from app.models.session import Session
from app.services.provider_utils import resolve_model_config

logger = structlog.get_logger()


def _iso_now() -> str:
    """Return current UTC time as ISO 8601 string."""
    return datetime.now(UTC).isoformat()


async def process_user_message(
    session_id: str,
    content: str,
    db: AsyncSession,
) -> AsyncGenerator[dict, None]:
    """Process a user message: call LLM, stream response, update transcript.

    Yields typed JSON envelope dicts suitable for WebSocket transmission:
    - {"type": "message_chunk", ...}  for each streamed content token
    - {"type": "tool_call", ...}      for each tool call in the response
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

    # 2. Resolve provider from agent_config and create backend adapter
    agent_config = session.agent_config or {}
    adapter = create_agent_backend(agent_config)

    # 3. Build messages array from transcript + new user message
    transcript = list(session.transcript or [])
    messages_for_llm: list[dict] = []

    # System prompt is passed separately to the adapter
    system_prompt = agent_config.get("system_prompt")
    has_system_in_transcript = any(e.get("role") == "system" for e in transcript)
    if has_system_in_transcript:
        # Already in transcript, don't pass separately
        system_prompt = None

    for entry in transcript:
        msg: dict = {"role": entry["role"], "content": entry.get("content", "")}
        if entry.get("tool_calls"):
            msg["tool_calls"] = entry["tool_calls"]
        messages_for_llm.append(msg)

    # Append the new user message
    user_message = {
        "role": "user",
        "content": content,
        "timestamp": _iso_now(),
    }
    messages_for_llm.append({"role": "user", "content": content})

    # 4. Persist user message to transcript
    transcript.append(user_message)
    session.transcript = transcript
    await db.commit()

    logger.info(
        "agent_chat.llm_call",
        session_id=session_id,
        model=adapter.model,
        message_count=len(messages_for_llm),
    )

    # 5. Stream the response via adapter
    full_content = ""
    accumulated_tool_calls: dict[int, dict] = {}  # index -> {id, name, arguments_str}

    async for chunk in adapter.send_message(messages_for_llm, system_prompt):
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
                # Accumulate partial data
                if tc.get("id"):
                    accumulated_tool_calls[idx]["id"] = tc["id"]
                if tc.get("name"):
                    accumulated_tool_calls[idx]["name"] += tc["name"]
                if tc.get("arguments"):
                    accumulated_tool_calls[idx]["arguments"] += tc["arguments"]

    # 7. Yield tool_call messages
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
        }
        tool_calls_list.append(tc_envelope)

        yield {
            "type": "tool_call",
            "data": tc_envelope,
            "timestamp": _iso_now(),
            "sender": "agent",
            "session_id": session_id,
        }

    # 8. Yield message_complete
    yield {
        "type": "message_complete",
        "data": {
            "content": full_content,
            "tool_calls": tool_calls_list,
        },
        "timestamp": _iso_now(),
        "sender": "agent",
        "session_id": session_id,
    }

    # 9. Persist assistant message to transcript
    assistant_message: dict = {
        "role": "assistant",
        "content": full_content,
        "timestamp": _iso_now(),
    }
    if tool_calls_list:
        assistant_message["tool_calls"] = tool_calls_list

    # Re-read transcript to get latest state (user message was already appended)
    await db.refresh(session)
    transcript = list(session.transcript or [])
    transcript.append(assistant_message)
    session.transcript = transcript
    await db.commit()

    logger.info(
        "agent_chat.message_complete",
        session_id=session_id,
        content_length=len(full_content),
        tool_call_count=len(tool_calls_list),
    )


async def end_and_score_session(session_id: str, db: AsyncSession) -> dict:
    """End a session and optionally score it with a judge.

    Args:
        session_id: The session to end.
        db: Async database session.

    Returns:
        Dict with session status and scores.

    Raises:
        ValueError: If session not found.
    """
    result = await db.execute(select(Session).where(Session.id == session_id))
    session = result.scalar_one_or_none()
    if not session:
        raise ValueError(f"Session '{session_id}' not found")

    session.status = "ended"
    session.ended_at = datetime.now(UTC)

    # Score with judge if configured
    if session.judge_config_snapshot:
        try:
            judge_config = session.judge_config_snapshot

            # Resolve judge model via provider registry or direct config
            judge_resolved = resolve_model_config(judge_config)

            judge_params = JudgeConfigParams(
                model=judge_resolved.model,
                temperature=judge_config.get("temperature", 0.0),
                prompt_template=judge_config.get("prompt_template"),
                pass_threshold=judge_config.get("pass_threshold", 0.7),
                dimensions=judge_config.get("dimensions"),
                aggregation=judge_config.get("aggregation"),
            )

            adapter = create_evaluation_adapter(
                model=judge_resolved.model,
                api_key=judge_resolved.api_key,
                api_base=judge_resolved.api_base,
            )

            # Convert transcript to adapter types
            transcript = session.transcript or []
            messages = [
                Message(
                    role=msg["role"],
                    content=msg.get("content", ""),
                )
                for msg in transcript
                if msg.get("role") in ("user", "assistant", "system")
            ]
            tool_calls = []
            for msg in transcript:
                for tc in msg.get("tool_calls", []):
                    tool_calls.append(
                        ToolCall(
                            tool_name=tc.get("tool_name", ""),
                            arguments=tc.get("arguments", {}),
                            result=tc.get("result"),
                            duration_ms=tc.get("duration_ms"),
                        )
                    )

            score = await adapter.evaluate_conversation(messages, tool_calls, judge_params)

            session.scores = {
                "overall": score.value,
                "passed": score.passed,
                "reasoning": score.reasoning,
                "breakdown": score.breakdown,
            }

            logger.info(
                "agent_chat.session_scored",
                session_id=session_id,
                score=score.value,
                passed=score.passed,
            )

        except Exception as exc:
            logger.exception("agent_chat.judge_error", session_id=session_id)
            session.error = f"Judge scoring failed: {exc}"

    await db.commit()

    return {
        "status": session.status,
        "scores": session.scores,
        "ended_at": session.ended_at.isoformat() if session.ended_at else None,
    }
