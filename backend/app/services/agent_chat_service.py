"""Agent chat service — orchestrates interactive LLM chat sessions.

Handles: resolving provider config, calling LLM via litellm (streaming),
parsing tool calls from streamed chunks, updating session transcript in DB,
and yielding typed JSON envelope messages for the WebSocket layer.
"""

import json
from collections.abc import AsyncGenerator
from datetime import UTC, datetime

import litellm
import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.base import JudgeConfigParams, Message, ToolCall
from app.adapters.litellm_judge import LiteLLMJudgeAdapter
from app.models.session import Session
from app.services.provider_utils import proxy_env, resolve_model_config

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

    # 2. Resolve provider from agent_config
    agent_config = session.agent_config or {}
    resolved = resolve_model_config(agent_config)

    # 3. Build messages array from transcript + new user message
    transcript = list(session.transcript or [])
    messages_for_llm = []
    for entry in transcript:
        msg = {"role": entry["role"], "content": entry.get("content", "")}
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

    # 5. Call LiteLLM with streaming
    litellm_kwargs: dict = {
        "model": resolved.model,
        "messages": messages_for_llm,
        "stream": True,
    }
    if resolved.api_key:
        litellm_kwargs["api_key"] = resolved.api_key
    if resolved.api_base:
        litellm_kwargs["api_base"] = resolved.api_base

    logger.info(
        "agent_chat.llm_call",
        session_id=session_id,
        model=resolved.model,
        message_count=len(messages_for_llm),
    )

    # 6. Stream the response
    full_content = ""
    accumulated_tool_calls: dict[int, dict] = {}  # index -> {id, name, arguments_str}

    with proxy_env(resolved.proxy):
        stream = await litellm.acompletion(**litellm_kwargs)
        async for chunk in stream:
            delta = chunk.choices[0].delta

            # Content tokens
            if delta.content:
                full_content += delta.content
                yield {
                    "type": "message_chunk",
                    "data": {"content": delta.content},
                    "timestamp": _iso_now(),
                    "sender": "agent",
                    "session_id": session_id,
                }

            # Tool call chunks (accumulated across multiple chunks)
            if delta.tool_calls:
                for tc_chunk in delta.tool_calls:
                    idx = tc_chunk.index
                    if idx not in accumulated_tool_calls:
                        accumulated_tool_calls[idx] = {
                            "id": tc_chunk.id or "",
                            "name": tc_chunk.function.name or "",
                            "arguments": tc_chunk.function.arguments or "",
                        }
                    else:
                        # Accumulate partial data
                        if tc_chunk.id:
                            accumulated_tool_calls[idx]["id"] = tc_chunk.id
                        if tc_chunk.function.name:
                            accumulated_tool_calls[idx]["name"] += tc_chunk.function.name
                        if tc_chunk.function.arguments:
                            accumulated_tool_calls[idx]["arguments"] += tc_chunk.function.arguments

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
            judge_params = JudgeConfigParams(
                model=judge_config.get("model"),
                temperature=judge_config.get("temperature", 0.0),
                prompt_template=judge_config.get("prompt_template"),
                pass_threshold=judge_config.get("pass_threshold", 0.7),
                dimensions=judge_config.get("dimensions"),
                aggregation=judge_config.get("aggregation"),
            )

            # Resolve judge provider
            judge_resolved = resolve_model_config(judge_config)

            adapter = LiteLLMJudgeAdapter(
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
