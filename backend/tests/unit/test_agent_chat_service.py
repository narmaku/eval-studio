"""Tests for agent_chat_service — streaming LLM chat with tool call parsing."""

import json
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.evaluation import Evaluation
from app.models.session import Session
from app.services.agent_chat_service import (
    _build_tool_calls,
    _transcript_to_llm_messages,
    end_session,
    process_user_message,
)


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
async def test_message_id_consistent_between_chunks_and_complete(db_session: AsyncSession, session_with_config):
    """ARCH-003: message_id is the same across all chunks and the complete envelope for one turn."""
    session = session_with_config

    mock_stream = _make_streaming_chunks("Hi!")

    with patch("app.agent_backends.litellm_agent.litellm.acompletion", new_callable=AsyncMock) as mock_acomp:
        mock_acomp.return_value = mock_stream

        messages = []
        async for msg in process_user_message(session.id, "Hello", db_session):
            messages.append(msg)

    chunks = [m for m in messages if m["type"] == "message_chunk"]
    completes = [m for m in messages if m["type"] == "message_complete"]

    assert len(chunks) == 3  # "Hi!" = 3 chars
    assert len(completes) == 1

    # All chunks share the same message_id
    chunk_ids = {c["data"]["message_id"] for c in chunks}
    assert len(chunk_ids) == 1

    # Complete has the same message_id
    complete_id = completes[0]["data"]["message_id"]
    assert complete_id in chunk_ids

    # message_id is a valid UUID
    import uuid

    uuid.UUID(complete_id)


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
async def test_end_session_sets_running_evaluation_to_completed(db_session: AsyncSession, session_with_config):
    """ARCH-006: end_session transitions a 'running' evaluation to 'completed'."""
    session = session_with_config

    # Set evaluation to running
    eval_result = await db_session.execute(select(Evaluation).where(Evaluation.id == session.evaluation_id))
    evaluation = eval_result.scalar_one()
    evaluation.status = "running"
    await db_session.flush()

    result = await end_session(session.id, db_session)
    assert result["status"] == "ended"

    eval_result = await db_session.execute(select(Evaluation).where(Evaluation.id == session.evaluation_id))
    evaluation = eval_result.scalar_one()
    assert evaluation.status == "completed"


@pytest.mark.asyncio
async def test_end_session_does_not_change_pending_evaluation(db_session: AsyncSession, session_with_config):
    """ARCH-006: end_session does NOT change a 'pending' evaluation status."""
    session = session_with_config

    result = await end_session(session.id, db_session)
    assert result["status"] == "ended"

    eval_result = await db_session.execute(select(Evaluation).where(Evaluation.id == session.evaluation_id))
    evaluation = eval_result.scalar_one()
    assert evaluation.status == "pending"


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


class TestTranscriptToLlmMessages:
    """Unit tests for the _transcript_to_llm_messages pure function."""

    def test_empty_transcript(self):
        assert _transcript_to_llm_messages([]) == []

    def test_user_and_assistant_messages(self):
        transcript = [
            {"role": "user", "content": "Hello", "timestamp": "2025-01-01T00:00:00Z"},
            {"role": "assistant", "content": "Hi!", "timestamp": "2025-01-01T00:00:01Z"},
        ]
        result = _transcript_to_llm_messages(transcript)
        assert result == [
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi!"},
        ]

    def test_system_prompt_in_transcript(self):
        transcript = [
            {"role": "system", "content": "You are helpful."},
            {"role": "user", "content": "Hello"},
        ]
        result = _transcript_to_llm_messages(transcript)
        assert result[0] == {"role": "system", "content": "You are helpful."}

    def test_assistant_with_tool_calls(self):
        transcript = [
            {
                "role": "assistant",
                "content": "Let me check.",
                "tool_calls": [
                    {"id": "call_1", "tool_name": "get_weather", "arguments": {"city": "NYC"}},
                ],
            },
        ]
        result = _transcript_to_llm_messages(transcript)
        assert len(result) == 1
        msg = result[0]
        assert msg["role"] == "assistant"
        assert msg["content"] == "Let me check."
        assert len(msg["tool_calls"]) == 1
        tc = msg["tool_calls"][0]
        assert tc["id"] == "call_1"
        assert tc["type"] == "function"
        assert tc["function"]["name"] == "get_weather"
        assert json.loads(tc["function"]["arguments"]) == {"city": "NYC"}

    def test_tool_result_message(self):
        transcript = [
            {"role": "tool", "tool_call_id": "call_1", "content": "72°F"},
        ]
        result = _transcript_to_llm_messages(transcript)
        assert result == [{"role": "tool", "tool_call_id": "call_1", "content": "72°F"}]

    def test_assistant_tool_calls_with_name_key(self):
        """Handles both 'tool_name' and 'name' keys (internal envelopes vs harness parsers)."""
        transcript = [
            {
                "role": "assistant",
                "content": "",
                "tool_calls": [{"id": "c1", "name": "my_tool", "arguments": {}}],
            },
        ]
        result = _transcript_to_llm_messages(transcript)
        assert result[0]["tool_calls"][0]["function"]["name"] == "my_tool"

    def test_empty_tool_arguments_workaround(self):
        """Empty arguments get the Gemini workaround placeholder."""
        transcript = [
            {
                "role": "assistant",
                "content": "",
                "tool_calls": [{"id": "c1", "tool_name": "ping", "arguments": {}}],
            },
        ]
        result = _transcript_to_llm_messages(transcript)
        assert result[0]["tool_calls"][0]["function"]["arguments"] == '{"_": ""}'


class TestBuildToolCalls:
    """Unit tests for _build_tool_calls."""

    def test_empty_accumulated(self):
        assert _build_tool_calls({}) == []

    def test_single_tool_call(self):
        accumulated = {0: {"id": "call_1", "name": "get_weather", "arguments": '{"city": "NYC"}'}}
        result = _build_tool_calls(accumulated)
        assert len(result) == 1
        assert result[0]["id"] == "call_1"
        assert result[0]["tool_name"] == "get_weather"
        assert result[0]["arguments"] == {"city": "NYC"}
        assert result[0]["status"] == "pending"
        assert result[0]["result"] is None

    def test_multiple_tool_calls_sorted_by_index(self):
        accumulated = {
            2: {"id": "c3", "name": "tool_c", "arguments": "{}"},
            0: {"id": "c1", "name": "tool_a", "arguments": "{}"},
            1: {"id": "c2", "name": "tool_b", "arguments": "{}"},
        }
        result = _build_tool_calls(accumulated)
        assert [tc["id"] for tc in result] == ["c1", "c2", "c3"]

    def test_malformed_json_arguments(self):
        accumulated = {0: {"id": "c1", "name": "tool", "arguments": "not valid json"}}
        result = _build_tool_calls(accumulated)
        assert result[0]["arguments"] == {"raw": "not valid json"}

    def test_empty_arguments_string(self):
        accumulated = {0: {"id": "c1", "name": "tool", "arguments": ""}}
        result = _build_tool_calls(accumulated)
        assert result[0]["arguments"] == {}


def _make_tool_result_mock(result_text: str = "tool output", is_error: bool = False, duration_ms: int = 42):
    """Create a mock tool result object."""
    result = MagicMock()
    result.result = result_text
    result.is_error = is_error
    result.duration_ms = duration_ms
    return result


@pytest.fixture
async def session_with_tools(db_session: AsyncSession):
    """Create a session with tool_server_ids configured for multi-round tests."""
    evaluation = Evaluation(
        name="Agent Tool Test",
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
        agent_config={
            "default_model": "openai/test-model",
            "api_base": "http://localhost:8080/v1",
            "tool_server_ids": ["server-1"],
        },
        transcript=[],
    )
    db_session.add(session)
    await db_session.commit()
    await db_session.refresh(session)
    return session


@pytest.mark.asyncio
async def test_per_round_message_ids(db_session: AsyncSession, session_with_tools):
    """Each agentic round uses a distinct message_id for its chunks and message_complete."""
    session = session_with_tools

    # Round 1: LLM returns text + tool_call
    round1_stream = _make_streaming_chunks(
        "Thinking...", tool_calls=[{"id": "call_1", "name": "search", "arguments": {"q": "test"}}]
    )
    # Round 2: LLM returns final text only
    round2_stream = _make_streaming_chunks("Here is the answer.")

    call_count = 0

    async def mock_acompletion(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            return round1_stream
        return round2_stream

    mock_manager = MagicMock()
    mock_manager.start_servers = AsyncMock(return_value=[{"type": "function", "function": {"name": "search"}}])
    mock_manager.call_tool = AsyncMock(return_value=_make_tool_result_mock())

    with (
        patch("app.agent_backends.litellm_agent.litellm.acompletion", side_effect=mock_acompletion),
        patch("app.services.agent_chat_service.get_or_create_manager", return_value=mock_manager),
    ):
        envelopes = []
        async for msg in process_user_message(session.id, "Find something", db_session):
            envelopes.append(msg)

    complete_msgs = [m for m in envelopes if m["type"] == "message_complete"]
    assert len(complete_msgs) == 2, f"Expected 2 message_complete envelopes, got {len(complete_msgs)}"

    # Each should have a different message_id
    ids = [m["data"]["message_id"] for m in complete_msgs]
    assert ids[0] != ids[1], "Each round must have a unique message_id"

    # Chunks for each round should match their round's message_complete id
    chunks = [m for m in envelopes if m["type"] == "message_chunk"]
    round1_chunks = [c for c in chunks if c["data"]["message_id"] == ids[0]]
    round2_chunks = [c for c in chunks if c["data"]["message_id"] == ids[1]]
    assert len(round1_chunks) > 0, "Round 1 should have chunks with its message_id"
    assert len(round2_chunks) > 0, "Round 2 should have chunks with its message_id"


@pytest.mark.asyncio
async def test_is_final_false_on_intermediate_rounds(db_session: AsyncSession, session_with_tools):
    """Intermediate rounds yield message_complete with is_final=False."""
    session = session_with_tools

    round1_stream = _make_streaming_chunks(
        "Let me look.", tool_calls=[{"id": "call_1", "name": "search", "arguments": {"q": "x"}}]
    )
    round2_stream = _make_streaming_chunks("Done.")

    call_count = 0

    async def mock_acompletion(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            return round1_stream
        return round2_stream

    mock_manager = MagicMock()
    mock_manager.start_servers = AsyncMock(return_value=[{"type": "function", "function": {"name": "search"}}])
    mock_manager.call_tool = AsyncMock(return_value=_make_tool_result_mock())

    with (
        patch("app.agent_backends.litellm_agent.litellm.acompletion", side_effect=mock_acompletion),
        patch("app.services.agent_chat_service.get_or_create_manager", return_value=mock_manager),
    ):
        envelopes = []
        async for msg in process_user_message(session.id, "Look up x", db_session):
            envelopes.append(msg)

    complete_msgs = [m for m in envelopes if m["type"] == "message_complete"]
    assert len(complete_msgs) == 2

    # First (intermediate) round: is_final=False
    assert complete_msgs[0]["data"]["is_final"] is False


@pytest.mark.asyncio
async def test_is_final_true_on_last_round(db_session: AsyncSession, session_with_tools):
    """The final round yields message_complete with is_final=True."""
    session = session_with_tools

    round1_stream = _make_streaming_chunks(
        "Checking.", tool_calls=[{"id": "call_1", "name": "search", "arguments": {"q": "y"}}]
    )
    round2_stream = _make_streaming_chunks("All done!")

    call_count = 0

    async def mock_acompletion(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            return round1_stream
        return round2_stream

    mock_manager = MagicMock()
    mock_manager.start_servers = AsyncMock(return_value=[{"type": "function", "function": {"name": "search"}}])
    mock_manager.call_tool = AsyncMock(return_value=_make_tool_result_mock())

    with (
        patch("app.agent_backends.litellm_agent.litellm.acompletion", side_effect=mock_acompletion),
        patch("app.services.agent_chat_service.get_or_create_manager", return_value=mock_manager),
    ):
        envelopes = []
        async for msg in process_user_message(session.id, "Look up y", db_session):
            envelopes.append(msg)

    complete_msgs = [m for m in envelopes if m["type"] == "message_complete"]
    assert len(complete_msgs) == 2

    # Last (final) round: is_final=True
    assert complete_msgs[-1]["data"]["is_final"] is True


@pytest.mark.asyncio
async def test_simple_response_has_is_final_true(db_session: AsyncSession, session_with_config):
    """A simple text-only response (no tools) yields message_complete with is_final=True."""
    session = session_with_config

    mock_stream = _make_streaming_chunks("Hello!")

    with patch("app.agent_backends.litellm_agent.litellm.acompletion", new_callable=AsyncMock) as mock_acomp:
        mock_acomp.return_value = mock_stream

        envelopes = []
        async for msg in process_user_message(session.id, "Hi", db_session):
            envelopes.append(msg)

    complete_msgs = [m for m in envelopes if m["type"] == "message_complete"]
    assert len(complete_msgs) == 1
    assert complete_msgs[0]["data"]["is_final"] is True


@pytest.mark.asyncio
async def test_max_rounds_with_content_emits_is_final_true(db_session: AsyncSession, session_with_tools):
    """When max_rounds is reached and the last round has content, is_final must be True.

    Regression test: previously, when the last tool-calling round had text content,
    the intermediate message_complete was emitted with is_final=False and the
    max_rounds guard did not emit a corrective is_final=True, leaving the frontend
    stuck in isProcessing=true.
    """
    session = session_with_tools

    # Every round returns text + tool call
    def make_tool_stream(round_num: int):
        return _make_streaming_chunks(
            f"Round {round_num} thinking...",
            tool_calls=[{"id": f"call_{round_num}", "name": "search", "arguments": {"q": f"r{round_num}"}}],
        )

    call_count = 0

    async def mock_acompletion(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        return make_tool_stream(call_count)

    mock_manager = MagicMock()
    mock_manager.start_servers = AsyncMock(return_value=[{"type": "function", "function": {"name": "search"}}])
    mock_manager.call_tool = AsyncMock(return_value=_make_tool_result_mock())

    with (
        patch("app.agent_backends.litellm_agent.litellm.acompletion", side_effect=mock_acompletion),
        patch("app.services.agent_chat_service.get_or_create_manager", return_value=mock_manager),
        patch("app.services.agent_chat_service.MAX_TOOL_ROUNDS", 2),
    ):
        envelopes = []
        async for msg in process_user_message(session.id, "Keep searching", db_session):
            envelopes.append(msg)

    complete_msgs = [m for m in envelopes if m["type"] == "message_complete"]
    assert len(complete_msgs) == 2, f"Expected 2 message_complete envelopes, got {len(complete_msgs)}"

    # The last message_complete MUST have is_final=True so the frontend exits isProcessing
    assert complete_msgs[-1]["data"]["is_final"] is True, "Last message_complete at max_rounds must have is_final=True"

    # Intermediate rounds should have is_final=False
    assert complete_msgs[0]["data"]["is_final"] is False


@pytest.mark.asyncio
async def test_empty_content_intermediate_round_skips_message_complete(db_session: AsyncSession, session_with_tools):
    """When an intermediate round has tool calls but no text, message_complete is skipped.

    The guard `if full_content or at_max_rounds` means an intermediate round with
    empty content produces no message_complete envelope for that round.
    """
    session = session_with_tools

    # Round 1: tool call only, no text content
    round1_stream = _make_streaming_chunks(
        "", tool_calls=[{"id": "call_1", "name": "search", "arguments": {"q": "test"}}]
    )
    # Round 2: final text response
    round2_stream = _make_streaming_chunks("Found the answer.")

    call_count = 0

    async def mock_acompletion(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            return round1_stream
        return round2_stream

    mock_manager = MagicMock()
    mock_manager.start_servers = AsyncMock(return_value=[{"type": "function", "function": {"name": "search"}}])
    mock_manager.call_tool = AsyncMock(return_value=_make_tool_result_mock())

    with (
        patch("app.agent_backends.litellm_agent.litellm.acompletion", side_effect=mock_acompletion),
        patch("app.services.agent_chat_service.get_or_create_manager", return_value=mock_manager),
    ):
        envelopes = []
        async for msg in process_user_message(session.id, "Find it", db_session):
            envelopes.append(msg)

    complete_msgs = [m for m in envelopes if m["type"] == "message_complete"]
    # Only the final round emits message_complete; the empty intermediate is skipped
    assert len(complete_msgs) == 1, f"Expected 1 message_complete (final only), got {len(complete_msgs)}"
    assert complete_msgs[0]["data"]["is_final"] is True
    assert complete_msgs[0]["data"]["content"] == "Found the answer."


@pytest.mark.asyncio
async def test_max_rounds_empty_content_still_emits_message_complete(db_session: AsyncSession, session_with_tools):
    """When max_rounds is hit and the last round has no text, message_complete is still emitted.

    The `at_max_rounds` branch of the guard ensures a message_complete is always
    emitted at max_rounds, even when full_content is empty.
    """
    session = session_with_tools

    def make_empty_content_stream(round_num: int):
        return _make_streaming_chunks(
            "", tool_calls=[{"id": f"call_{round_num}", "name": "search", "arguments": {"q": f"r{round_num}"}}]
        )

    call_count = 0

    async def mock_acompletion(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        return make_empty_content_stream(call_count)

    mock_manager = MagicMock()
    mock_manager.start_servers = AsyncMock(return_value=[{"type": "function", "function": {"name": "search"}}])
    mock_manager.call_tool = AsyncMock(return_value=_make_tool_result_mock())

    with (
        patch("app.agent_backends.litellm_agent.litellm.acompletion", side_effect=mock_acompletion),
        patch("app.services.agent_chat_service.get_or_create_manager", return_value=mock_manager),
        patch("app.services.agent_chat_service.MAX_TOOL_ROUNDS", 2),
    ):
        envelopes = []
        async for msg in process_user_message(session.id, "Keep going", db_session):
            envelopes.append(msg)

    complete_msgs = [m for m in envelopes if m["type"] == "message_complete"]
    # Only the max_rounds message_complete (intermediate empties are skipped)
    assert len(complete_msgs) == 1, f"Expected 1 message_complete at max_rounds, got {len(complete_msgs)}"
    assert complete_msgs[0]["data"]["is_final"] is True
    assert complete_msgs[0]["data"]["content"] == ""


@pytest.mark.asyncio
async def test_unexecutable_tool_calls_has_is_final_true(db_session: AsyncSession, session_with_config):
    """When tool calls exist but no tool servers are configured, is_final is True.

    Tests the else branch where tool_calls are present but can't be executed
    because the session has no tool_server_ids.
    """
    session = session_with_config  # No tool_server_ids

    tool_calls = [
        {"id": "call_unexec", "name": "unavailable_tool", "arguments": {"arg": "val"}},
    ]
    mock_stream = _make_streaming_chunks("I'll try this tool.", tool_calls=tool_calls)

    with patch("app.agent_backends.litellm_agent.litellm.acompletion", new_callable=AsyncMock) as mock_acomp:
        mock_acomp.return_value = mock_stream

        envelopes = []
        async for msg in process_user_message(session.id, "Do something", db_session):
            envelopes.append(msg)

    complete_msgs = [m for m in envelopes if m["type"] == "message_complete"]
    assert len(complete_msgs) == 1
    assert complete_msgs[0]["data"]["is_final"] is True
    assert complete_msgs[0]["data"]["content"] == "I'll try this tool."
    assert len(complete_msgs[0]["data"]["tool_calls"]) == 1


@pytest.mark.asyncio
async def test_three_round_agentic_loop(db_session: AsyncSession, session_with_tools):
    """A 3-round agentic loop produces correct is_final flags across all rounds.

    Round 1: tool call with text -> is_final=False
    Round 2: tool call with text -> is_final=False
    Round 3: text only -> is_final=True
    """
    session = session_with_tools

    round1_stream = _make_streaming_chunks(
        "Step 1.", tool_calls=[{"id": "call_1", "name": "search", "arguments": {"q": "a"}}]
    )
    round2_stream = _make_streaming_chunks(
        "Step 2.", tool_calls=[{"id": "call_2", "name": "search", "arguments": {"q": "b"}}]
    )
    round3_stream = _make_streaming_chunks("Final answer.")

    call_count = 0

    async def mock_acompletion(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            return round1_stream
        elif call_count == 2:
            return round2_stream
        return round3_stream

    mock_manager = MagicMock()
    mock_manager.start_servers = AsyncMock(return_value=[{"type": "function", "function": {"name": "search"}}])
    mock_manager.call_tool = AsyncMock(return_value=_make_tool_result_mock())

    with (
        patch("app.agent_backends.litellm_agent.litellm.acompletion", side_effect=mock_acompletion),
        patch("app.services.agent_chat_service.get_or_create_manager", return_value=mock_manager),
    ):
        envelopes = []
        async for msg in process_user_message(session.id, "Multi-step task", db_session):
            envelopes.append(msg)

    complete_msgs = [m for m in envelopes if m["type"] == "message_complete"]
    assert len(complete_msgs) == 3, f"Expected 3 message_complete envelopes, got {len(complete_msgs)}"

    # All message_ids must be unique
    ids = [m["data"]["message_id"] for m in complete_msgs]
    assert len(set(ids)) == 3, "All 3 rounds must have unique message_ids"

    # is_final progression: False, False, True
    assert complete_msgs[0]["data"]["is_final"] is False
    assert complete_msgs[1]["data"]["is_final"] is False
    assert complete_msgs[2]["data"]["is_final"] is True

    # Content progression
    assert complete_msgs[0]["data"]["content"] == "Step 1."
    assert complete_msgs[1]["data"]["content"] == "Step 2."
    assert complete_msgs[2]["data"]["content"] == "Final answer."
