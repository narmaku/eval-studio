"""Unit tests for the LiteLLM agent backend adapter."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.agent_backends.base import AgentStreamChunk
from app.agent_backends.litellm_agent import LiteLLMAgentAdapter


def _make_streaming_chunks(content: str, tool_calls: list | None = None):
    """Create mock streaming chunk objects simulating litellm.acompletion(stream=True).

    Returns an async iterator of chunk objects.
    """
    chunks = []

    # Content chunks (one per character for testing)
    for char in content:
        chunk = MagicMock()
        chunk.choices = [MagicMock()]
        chunk.choices[0].delta = MagicMock()
        chunk.choices[0].delta.content = char
        chunk.choices[0].delta.tool_calls = None
        chunks.append(chunk)

    # Tool call chunks
    if tool_calls:
        for tc in tool_calls:
            chunk = MagicMock()
            chunk.choices = [MagicMock()]
            chunk.choices[0].delta = MagicMock()
            chunk.choices[0].delta.content = None
            tc_mock = MagicMock()
            tc_mock.index = tc.get("index", 0)
            tc_mock.id = tc.get("id", "call_123")
            tc_mock.function = MagicMock()
            tc_mock.function.name = tc["name"]
            tc_mock.function.arguments = tc.get("arguments", "{}")
            chunk.choices[0].delta.tool_calls = [tc_mock]
            chunks.append(chunk)

    # Final empty chunk
    final = MagicMock()
    final.choices = [MagicMock()]
    final.choices[0].delta = MagicMock()
    final.choices[0].delta.content = None
    final.choices[0].delta.tool_calls = None
    chunks.append(final)

    async def async_gen():
        for c in chunks:
            yield c

    return async_gen()


@pytest.mark.asyncio
async def test_send_message_streams_content():
    """send_message yields AgentStreamChunks with content from LiteLLM."""
    adapter = LiteLLMAgentAdapter(
        model="openai/gpt-4",
        api_key="sk-test",
        api_base="http://localhost:8080/v1",
    )

    mock_stream = _make_streaming_chunks("Hi!")

    with patch(
        "app.agent_backends.litellm_agent.litellm.acompletion",
        new_callable=AsyncMock,
        return_value=mock_stream,
    ) as mock_acomp:
        chunks: list[AgentStreamChunk] = []
        async for chunk in adapter.send_message(
            [{"role": "user", "content": "Hello"}],
        ):
            chunks.append(chunk)

    # Should have content chunks + done chunk
    content_chunks = [c for c in chunks if c.content is not None]
    done_chunks = [c for c in chunks if c.done]

    assert len(content_chunks) == 3  # "Hi!" = 3 chars
    assert "".join(c.content for c in content_chunks) == "Hi!"
    assert len(done_chunks) == 1

    # Verify LiteLLM was called correctly
    mock_acomp.assert_called_once()
    call_kwargs = mock_acomp.call_args[1]
    assert call_kwargs["model"] == "openai/gpt-4"
    assert call_kwargs["api_key"] == "sk-test"
    assert call_kwargs["api_base"] == "http://localhost:8080/v1"
    assert call_kwargs["stream"] is True


@pytest.mark.asyncio
async def test_send_message_with_system_prompt():
    """send_message prepends system prompt when provided."""
    adapter = LiteLLMAgentAdapter(model="openai/gpt-4", api_key="sk-test")

    mock_stream = _make_streaming_chunks("OK")

    with patch(
        "app.agent_backends.litellm_agent.litellm.acompletion",
        new_callable=AsyncMock,
        return_value=mock_stream,
    ) as mock_acomp:
        chunks = []
        async for chunk in adapter.send_message(
            [{"role": "user", "content": "Hello"}],
            system_prompt="You are helpful.",
        ):
            chunks.append(chunk)

    call_kwargs = mock_acomp.call_args[1]
    messages = call_kwargs["messages"]
    assert messages[0]["role"] == "system"
    assert messages[0]["content"] == "You are helpful."
    assert messages[1]["role"] == "user"


@pytest.mark.asyncio
async def test_send_message_with_tool_calls():
    """send_message yields AgentStreamChunks with tool_call_chunk data."""
    adapter = LiteLLMAgentAdapter(model="openai/gpt-4", api_key="sk-test")

    tool_calls = [
        {"id": "call_abc", "name": "check_disk", "arguments": '{"path": "/"}', "index": 0},
    ]
    mock_stream = _make_streaming_chunks("Let me check.", tool_calls=tool_calls)

    with patch(
        "app.agent_backends.litellm_agent.litellm.acompletion",
        new_callable=AsyncMock,
        return_value=mock_stream,
    ):
        chunks = []
        async for chunk in adapter.send_message(
            [{"role": "user", "content": "Check disk"}],
        ):
            chunks.append(chunk)

    tc_chunks = [c for c in chunks if c.tool_call_chunk is not None]
    assert len(tc_chunks) == 1
    assert tc_chunks[0].tool_call_chunk["name"] == "check_disk"
    assert tc_chunks[0].tool_call_chunk["id"] == "call_abc"
    assert tc_chunks[0].tool_call_chunk["index"] == 0


@pytest.mark.asyncio
async def test_send_message_no_api_key():
    """send_message omits api_key from litellm kwargs when None."""
    adapter = LiteLLMAgentAdapter(model="openai/gpt-4")

    mock_stream = _make_streaming_chunks("OK")

    with patch(
        "app.agent_backends.litellm_agent.litellm.acompletion",
        new_callable=AsyncMock,
        return_value=mock_stream,
    ) as mock_acomp:
        async for _ in adapter.send_message([{"role": "user", "content": "Hi"}]):
            pass

    call_kwargs = mock_acomp.call_args[1]
    assert "api_key" not in call_kwargs
    assert "api_base" not in call_kwargs


@pytest.mark.asyncio
async def test_health_check():
    """health_check returns True."""
    adapter = LiteLLMAgentAdapter(model="openai/gpt-4")
    result = await adapter.health_check()
    assert result is True
