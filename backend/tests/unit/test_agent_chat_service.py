"""Tests for agent_chat_service — streaming LLM chat with tool call parsing."""

import json
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.evaluation import Evaluation
from app.models.session import Session
from app.services.agent_chat_service import end_and_score_session, process_user_message


def _make_streaming_chunks(content: str, tool_calls: list | None = None):
    """Create mock streaming chunk objects simulating litellm.acompletion(stream=True).

    Returns an async iterator of chunk objects.
    """
    chunks = []

    # Content chunks
    for _i, char in enumerate(content):
        chunk = MagicMock()
        chunk.choices = [MagicMock()]
        chunk.choices[0].delta = MagicMock()
        chunk.choices[0].delta.content = char
        chunk.choices[0].delta.tool_calls = None
        chunks.append(chunk)

    # Tool call chunks (sent after content)
    if tool_calls:
        for tc in tool_calls:
            chunk = MagicMock()
            chunk.choices = [MagicMock()]
            chunk.choices[0].delta = MagicMock()
            chunk.choices[0].delta.content = None
            tc_mock = MagicMock()
            tc_mock.index = 0
            tc_mock.id = tc.get("id", "call_123")
            tc_mock.function = MagicMock()
            tc_mock.function.name = tc["name"]
            tc_mock.function.arguments = json.dumps(tc["arguments"])
            chunk.choices[0].delta.tool_calls = [tc_mock]
            chunks.append(chunk)

    # Final chunk with empty content
    final_chunk = MagicMock()
    final_chunk.choices = [MagicMock()]
    final_chunk.choices[0].delta = MagicMock()
    final_chunk.choices[0].delta.content = None
    final_chunk.choices[0].delta.tool_calls = None
    chunks.append(final_chunk)

    async def async_gen():
        for c in chunks:
            yield c

    return async_gen()


@pytest.fixture
async def session_with_config(db_session: AsyncSession):
    """Create an evaluation and session with agent_config for testing."""
    evaluation = Evaluation(
        name="Agent Test Eval",
        mode="agent",
        status="pending",
        config={},
    )
    db_session.add(evaluation)
    await db_session.flush()

    session = Session(
        evaluation_id=evaluation.id,
        status="active",
        mode="live",
        agent_config={"default_model": "openai/test-model", "api_base": "http://localhost:8080/v1"},
        transcript=[],
    )
    db_session.add(session)
    await db_session.commit()
    await db_session.refresh(session)
    return session


@pytest.mark.asyncio
async def test_process_user_message_streams_content(db_session: AsyncSession, session_with_config):
    """process_user_message yields message_chunk and message_complete messages."""
    session = session_with_config

    mock_stream = _make_streaming_chunks("Hello!")

    with patch("app.agent_backends.litellm_agent.litellm.acompletion", new_callable=AsyncMock) as mock_acomp:
        mock_acomp.return_value = mock_stream

        messages = []
        async for msg in process_user_message(session.id, "Hi there", db_session):
            messages.append(msg)

    # Should have chunk messages for each character + message_complete
    chunk_messages = [m for m in messages if m["type"] == "message_chunk"]
    complete_messages = [m for m in messages if m["type"] == "message_complete"]

    assert len(chunk_messages) == 6  # "Hello!" = 6 chars
    assert len(complete_messages) == 1
    assert complete_messages[0]["data"]["content"] == "Hello!"
    assert complete_messages[0]["sender"] == "agent"
    assert complete_messages[0]["session_id"] == session.id

    # Verify transcript was updated in DB
    result = await db_session.execute(select(Session).where(Session.id == session.id))
    updated = result.scalar_one()
    assert len(updated.transcript) == 2  # user message + assistant message
    assert updated.transcript[0]["role"] == "user"
    assert updated.transcript[0]["content"] == "Hi there"
    assert updated.transcript[1]["role"] == "assistant"
    assert updated.transcript[1]["content"] == "Hello!"


@pytest.mark.asyncio
async def test_process_user_message_with_tool_calls(db_session: AsyncSession, session_with_config):
    """process_user_message yields tool_call messages when LLM returns tool calls."""
    session = session_with_config

    tool_calls = [
        {"id": "call_abc", "name": "check_disk", "arguments": {"path": "/"}},
    ]
    mock_stream = _make_streaming_chunks("Let me check.", tool_calls=tool_calls)

    with patch("app.agent_backends.litellm_agent.litellm.acompletion", new_callable=AsyncMock) as mock_acomp:
        mock_acomp.return_value = mock_stream

        messages = []
        async for msg in process_user_message(session.id, "Check disk", db_session):
            messages.append(msg)

    tool_call_msgs = [m for m in messages if m["type"] == "tool_call"]
    assert len(tool_call_msgs) == 1
    assert tool_call_msgs[0]["data"]["tool_name"] == "check_disk"
    assert tool_call_msgs[0]["data"]["arguments"] == {"path": "/"}
    assert tool_call_msgs[0]["data"]["id"] == "call_abc"

    complete_messages = [m for m in messages if m["type"] == "message_complete"]
    assert len(complete_messages) == 1
    assert len(complete_messages[0]["data"]["tool_calls"]) == 1

    # Verify transcript includes tool_calls
    result = await db_session.execute(select(Session).where(Session.id == session.id))
    updated = result.scalar_one()
    assistant_msg = updated.transcript[-1]
    assert assistant_msg["role"] == "assistant"
    assert "tool_calls" in assistant_msg
    assert len(assistant_msg["tool_calls"]) == 1


@pytest.mark.asyncio
async def test_process_user_message_inactive_session(db_session: AsyncSession, session_with_config):
    """process_user_message raises ValueError for non-active sessions."""
    session = session_with_config
    session.status = "ended"
    await db_session.commit()

    with pytest.raises(ValueError, match="not active"):
        async for _ in process_user_message(session.id, "test", db_session):
            pass


@pytest.mark.asyncio
async def test_process_user_message_session_not_found(db_session: AsyncSession):
    """process_user_message raises ValueError for nonexistent session."""
    with pytest.raises(ValueError, match="not found"):
        async for _ in process_user_message("nonexistent-id", "test", db_session):
            pass


@pytest.mark.asyncio
async def test_end_and_score_session_without_judge(db_session: AsyncSession, session_with_config):
    """end_and_score_session ends the session when no judge is configured."""
    session = session_with_config

    result = await end_and_score_session(session.id, db_session)

    assert result["status"] == "ended"
    assert result["scores"] is None

    # Verify DB state
    db_result = await db_session.execute(select(Session).where(Session.id == session.id))
    updated = db_result.scalar_one()
    assert updated.status == "ended"
    assert updated.ended_at is not None


@pytest.mark.asyncio
async def test_end_and_score_session_with_judge(db_session: AsyncSession, session_with_config):
    """end_and_score_session calls judge and stores scores."""
    session = session_with_config
    session.judge_config_snapshot = {"model": "judge-model", "pass_threshold": 0.7}
    session.transcript = [
        {"role": "user", "content": "Hello", "timestamp": datetime.now(UTC).isoformat()},
        {"role": "assistant", "content": "Hi!", "timestamp": datetime.now(UTC).isoformat()},
    ]
    await db_session.commit()

    mock_score = MagicMock()
    mock_score.value = 0.9
    mock_score.passed = True
    mock_score.reasoning = "Great conversation"
    mock_score.breakdown = {"helpfulness": 0.9}

    with patch(
        "app.adapters.litellm_judge.LiteLLMJudgeAdapter.evaluate_conversation",
        new_callable=AsyncMock,
        return_value=mock_score,
    ):
        result = await end_and_score_session(session.id, db_session)

    assert result["scores"]["overall"] == 0.9
    assert result["scores"]["passed"] is True
    assert result["scores"]["reasoning"] == "Great conversation"

    # Verify DB state
    db_result = await db_session.execute(select(Session).where(Session.id == session.id))
    updated = db_result.scalar_one()
    assert updated.scores is not None
    assert updated.scores["overall"] == 0.9


@pytest.mark.asyncio
async def test_end_and_score_session_judge_error(db_session: AsyncSession, session_with_config):
    """end_and_score_session stores error when judge fails but still ends session."""
    session = session_with_config
    session.judge_config_snapshot = {"model": "judge-model"}
    session.transcript = [
        {"role": "user", "content": "Hello", "timestamp": datetime.now(UTC).isoformat()},
    ]
    await db_session.commit()

    with patch(
        "app.adapters.litellm_judge.LiteLLMJudgeAdapter.evaluate_conversation",
        new_callable=AsyncMock,
        side_effect=RuntimeError("Judge API down"),
    ):
        result = await end_and_score_session(session.id, db_session)

    assert result["status"] == "ended"
    assert result["scores"] is None

    # Verify error was stored
    db_result = await db_session.execute(select(Session).where(Session.id == session.id))
    updated = db_result.scalar_one()
    assert updated.error is not None
    assert "Judge scoring failed" in updated.error
    # RuntimeError details should be sanitized — the raw message must NOT leak
    assert "Judge API down" not in updated.error
    assert updated.status == "ended"
