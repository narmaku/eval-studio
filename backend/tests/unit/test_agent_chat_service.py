"""Tests for agent_chat_service — streaming LLM chat with tool call parsing."""

import json
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.evaluation import Evaluation
from app.models.session import Session
from app.services.agent_chat_service import end_session, process_user_message


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
async def test_end_session_without_judge(db_session: AsyncSession, session_with_config):
    """end_session ends the session without scoring, even if judge is configured."""
    session = session_with_config

    result = await end_session(session.id, db_session)

    assert result["status"] == "ended"
    assert "scores" not in result

    # Verify DB state
    db_result = await db_session.execute(select(Session).where(Session.id == session.id))
    updated = db_result.scalar_one()
    assert updated.status == "ended"
    assert updated.ended_at is not None
    assert updated.scores is None


@pytest.mark.asyncio
async def test_end_session_does_not_score_even_with_judge_config(db_session: AsyncSession, session_with_config):
    """end_session does NOT invoke the judge, even when judge_config_snapshot is present."""
    session = session_with_config
    session.judge_config_snapshot = {"model": "judge-model", "pass_threshold": 0.7}
    session.transcript = [
        {"role": "user", "content": "Hello", "timestamp": datetime.now(UTC).isoformat()},
        {"role": "assistant", "content": "Hi!", "timestamp": datetime.now(UTC).isoformat()},
    ]
    await db_session.commit()

    with patch(
        "app.adapters.litellm_judge.LiteLLMJudgeAdapter.evaluate_conversation",
        new_callable=AsyncMock,
    ) as mock_judge:
        result = await end_session(session.id, db_session)

    # Judge should NOT have been called
    mock_judge.assert_not_called()

    assert result["status"] == "ended"
    assert "scores" not in result

    # Verify DB state — no scores stored
    db_result = await db_session.execute(select(Session).where(Session.id == session.id))
    updated = db_result.scalar_one()
    assert updated.scores is None
    assert updated.status == "ended"
    assert updated.ended_at is not None


@pytest.mark.asyncio
async def test_end_session_sets_evaluation_to_completed(db_session: AsyncSession, session_with_config):
    """end_session sets the linked evaluation status to 'completed'."""
    session = session_with_config

    # Verify the evaluation starts as non-completed
    eval_result = await db_session.execute(select(Evaluation).where(Evaluation.id == session.evaluation_id))
    evaluation = eval_result.scalar_one()
    assert evaluation.status != "completed"

    result = await end_session(session.id, db_session)

    assert result["status"] == "ended"

    # Verify evaluation is now completed
    eval_result = await db_session.execute(select(Evaluation).where(Evaluation.id == session.evaluation_id))
    evaluation = eval_result.scalar_one()
    assert evaluation.status == "completed"


@pytest.mark.asyncio
async def test_end_session_does_not_create_result(db_session: AsyncSession, session_with_config):
    """end_session does NOT create a Result record — that is the score endpoint's job."""
    from app.models.result import Result

    session = session_with_config

    await end_session(session.id, db_session)

    # Verify no Result was created
    result_query = await db_session.execute(select(Result).where(Result.session_id == session.id))
    results = result_query.scalars().all()
    assert len(results) == 0


@pytest.mark.asyncio
async def test_end_session_idempotent(db_session: AsyncSession, session_with_config):
    """end_session is idempotent — calling it on an already-ended session returns current state."""
    session = session_with_config

    result1 = await end_session(session.id, db_session)
    assert result1["status"] == "ended"

    result2 = await end_session(session.id, db_session)
    assert result2["status"] == "ended"
    assert result2["ended_at"] is not None
