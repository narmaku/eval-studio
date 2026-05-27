"""Tests for LiteLLMJudgeAdapter conversation evaluation."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.adapters.base import JudgeConfigParams, Message, Score, ToolCall
from app.adapters.litellm_judge import LiteLLMJudgeAdapter


def _make_adapter(**kwargs) -> LiteLLMJudgeAdapter:
    defaults = {"model": "test-model", "max_concurrency": 5}
    defaults.update(kwargs)
    return LiteLLMJudgeAdapter(**defaults)


def _make_judge_config(**kwargs) -> JudgeConfigParams:
    defaults = {
        "model": "test-model",
        "temperature": 0.0,
        "prompt_template": None,
        "pass_threshold": 0.7,
    }
    defaults.update(kwargs)
    return JudgeConfigParams(**defaults)


def _sample_messages() -> list[Message]:
    return [
        Message(role="user", content="How do I restart the nginx service?"),
        Message(role="assistant", content="You can restart nginx with: sudo systemctl restart nginx"),
        Message(role="user", content="It says permission denied."),
        Message(role="assistant", content="Let me check the service status for you."),
    ]


def _sample_tool_calls() -> list[ToolCall]:
    return [
        ToolCall(
            tool_name="run_command",
            arguments={"command": "systemctl status nginx"},
            result="nginx.service - A high performance web server\n   Active: inactive (dead)",
            duration_ms=120,
        ),
        ToolCall(
            tool_name="run_command",
            arguments={"command": "sudo systemctl restart nginx"},
            result="",
            duration_ms=350,
        ),
    ]


def _mock_llm_response(content: str) -> MagicMock:
    mock = MagicMock()
    mock.choices = [MagicMock()]
    mock.choices[0].message.content = content
    return mock


@pytest.mark.asyncio
async def test_evaluate_conversation_success():
    """Valid JSON with all 4 dimensions returns correct Score with breakdown."""
    adapter = _make_adapter()
    judge_config = _make_judge_config()

    response_json = (
        '{"relevance": 0.9, "tool_use_accuracy": 0.85, "resolution": 0.8, '
        '"response_quality": 0.95, "overall": 0.875, "reasoning": "Good conversation overall."}'
    )
    mock_response = _mock_llm_response(response_json)

    with patch(
        "app.adapters.litellm_judge.litellm.acompletion",
        new_callable=AsyncMock,
        return_value=mock_response,
    ):
        score = await adapter.evaluate_conversation(
            messages=_sample_messages(),
            tool_calls=_sample_tool_calls(),
            judge_config=judge_config,
        )

    assert isinstance(score, Score)
    # Overall is mean of 4 dimensions: (0.9 + 0.85 + 0.8 + 0.95) / 4 = 0.875
    assert score.value == pytest.approx(0.875, abs=1e-6)
    assert score.passed is True  # 0.875 >= 0.7
    assert score.reasoning == "Good conversation overall."
    assert score.breakdown is not None
    assert score.breakdown["relevance"] == pytest.approx(0.9)
    assert score.breakdown["tool_use_accuracy"] == pytest.approx(0.85)
    assert score.breakdown["resolution"] == pytest.approx(0.8)
    assert score.breakdown["response_quality"] == pytest.approx(0.95)


@pytest.mark.asyncio
async def test_evaluate_conversation_empty():
    """Empty messages list returns neutral Score(0.5) without calling LLM."""
    adapter = _make_adapter()
    judge_config = _make_judge_config()

    with patch(
        "app.adapters.litellm_judge.litellm.acompletion",
        new_callable=AsyncMock,
    ) as mock_completion:
        score = await adapter.evaluate_conversation(
            messages=[],
            tool_calls=[],
            judge_config=judge_config,
        )

    mock_completion.assert_not_called()
    assert score.value == 0.5
    assert score.passed is False
    assert "Empty conversation" in score.reasoning


@pytest.mark.asyncio
async def test_evaluate_conversation_no_tool_calls():
    """Messages only, no tool calls -- still scores all 4 dimensions."""
    adapter = _make_adapter()
    judge_config = _make_judge_config()

    response_json = (
        '{"relevance": 0.9, "tool_use_accuracy": 0.5, "resolution": 0.7, '
        '"response_quality": 0.8, "overall": 0.725, "reasoning": "No tools were used."}'
    )
    mock_response = _mock_llm_response(response_json)

    with patch(
        "app.adapters.litellm_judge.litellm.acompletion",
        new_callable=AsyncMock,
        return_value=mock_response,
    ) as mock_completion:
        score = await adapter.evaluate_conversation(
            messages=_sample_messages(),
            tool_calls=[],
            judge_config=judge_config,
        )

    mock_completion.assert_called_once()
    assert score.value == pytest.approx(0.725, abs=1e-6)
    assert score.passed is True  # 0.725 >= 0.7
    assert score.breakdown is not None
    assert score.breakdown["tool_use_accuracy"] == pytest.approx(0.5)


@pytest.mark.asyncio
async def test_evaluate_conversation_long_transcript():
    """60 messages triggers truncation -- prompt contains 'messages omitted'."""
    adapter = _make_adapter()
    judge_config = _make_judge_config()

    long_messages = [
        Message(role="user" if i % 2 == 0 else "assistant", content=f"Message number {i}") for i in range(60)
    ]

    response_json = (
        '{"relevance": 0.7, "tool_use_accuracy": 0.7, "resolution": 0.7, '
        '"response_quality": 0.7, "overall": 0.7, "reasoning": "Truncated but ok."}'
    )
    mock_response = _mock_llm_response(response_json)

    with patch(
        "app.adapters.litellm_judge.litellm.acompletion",
        new_callable=AsyncMock,
        return_value=mock_response,
    ) as mock_completion:
        score = await adapter.evaluate_conversation(
            messages=long_messages,
            tool_calls=[],
            judge_config=judge_config,
        )

    mock_completion.assert_called_once()
    # Verify the prompt sent to the LLM contains truncation marker
    call_kwargs = mock_completion.call_args[1]
    prompt_content = call_kwargs["messages"][0]["content"]
    assert "messages omitted" in prompt_content
    assert score.value == pytest.approx(0.7, abs=1e-6)


@pytest.mark.asyncio
async def test_evaluate_conversation_parse_error():
    """Invalid JSON from LLM returns fallback Score(0.0) with error reasoning."""
    adapter = _make_adapter()
    judge_config = _make_judge_config()

    mock_response = _mock_llm_response("This is not valid JSON at all")

    with patch(
        "app.adapters.litellm_judge.litellm.acompletion",
        new_callable=AsyncMock,
        return_value=mock_response,
    ):
        score = await adapter.evaluate_conversation(
            messages=_sample_messages(),
            tool_calls=_sample_tool_calls(),
            judge_config=judge_config,
        )

    assert score.value == 0.0
    assert score.passed is False
    assert "Failed to parse" in score.reasoning


@pytest.mark.asyncio
async def test_evaluate_conversation_partial_scores():
    """Only 2 of 4 dimensions present -- missing ones default to 0.0."""
    adapter = _make_adapter()
    judge_config = _make_judge_config()

    response_json = '{"relevance": 0.8, "resolution": 0.6, "reasoning": "Partial scores."}'
    mock_response = _mock_llm_response(response_json)

    with patch(
        "app.adapters.litellm_judge.litellm.acompletion",
        new_callable=AsyncMock,
        return_value=mock_response,
    ):
        score = await adapter.evaluate_conversation(
            messages=_sample_messages(),
            tool_calls=_sample_tool_calls(),
            judge_config=judge_config,
        )

    # Overall = (0.8 + 0.0 + 0.6 + 0.0) / 4 = 0.35
    assert score.value == pytest.approx(0.35, abs=1e-6)
    assert score.passed is False  # 0.35 < 0.7
    assert score.breakdown["relevance"] == pytest.approx(0.8)
    assert score.breakdown["tool_use_accuracy"] == pytest.approx(0.0)
    assert score.breakdown["resolution"] == pytest.approx(0.6)
    assert score.breakdown["response_quality"] == pytest.approx(0.0)


@pytest.mark.asyncio
async def test_evaluate_conversation_none_content():
    """LLM returns None content -- returns fallback Score(0.0)."""
    adapter = _make_adapter()
    judge_config = _make_judge_config()

    mock_response = _mock_llm_response(None)

    with patch(
        "app.adapters.litellm_judge.litellm.acompletion",
        new_callable=AsyncMock,
        return_value=mock_response,
    ):
        score = await adapter.evaluate_conversation(
            messages=_sample_messages(),
            tool_calls=_sample_tool_calls(),
            judge_config=judge_config,
        )

    assert score.value == 0.0
    assert score.passed is False
    assert "empty response" in score.reasoning


@pytest.mark.asyncio
async def test_supports_mode_agent():
    """Adapter supports 'agent' mode after implementation."""
    adapter = _make_adapter()
    assert adapter.supports_mode("agent") is True
    assert adapter.supports_mode("qa") is True
    assert adapter.supports_mode("rag") is True


@pytest.mark.asyncio
async def test_available_metrics_includes_conversation():
    """get_available_metrics() includes conversation dimension names."""
    adapter = _make_adapter()
    metrics = await adapter.get_available_metrics()
    assert "correctness" in metrics
    assert "relevance" in metrics
    assert "tool_use_accuracy" in metrics
    assert "resolution" in metrics
    assert "response_quality" in metrics


@pytest.mark.asyncio
async def test_evaluate_conversation_custom_threshold():
    """Custom pass_threshold from judge_config is applied."""
    adapter = _make_adapter()
    judge_config = _make_judge_config(pass_threshold=0.9)

    response_json = (
        '{"relevance": 0.85, "tool_use_accuracy": 0.85, "resolution": 0.85, '
        '"response_quality": 0.85, "overall": 0.85, "reasoning": "High bar."}'
    )
    mock_response = _mock_llm_response(response_json)

    with patch(
        "app.adapters.litellm_judge.litellm.acompletion",
        new_callable=AsyncMock,
        return_value=mock_response,
    ):
        score = await adapter.evaluate_conversation(
            messages=_sample_messages(),
            tool_calls=_sample_tool_calls(),
            judge_config=judge_config,
        )

    assert score.value == pytest.approx(0.85, abs=1e-6)
    assert score.passed is False  # 0.85 < 0.9 threshold


@pytest.mark.asyncio
async def test_evaluate_conversation_api_key_and_base():
    """api_key and api_base are forwarded to LiteLLM when set."""
    adapter = _make_adapter(api_key="sk-test-key", api_base="http://localhost:4000")
    judge_config = _make_judge_config()

    response_json = (
        '{"relevance": 0.7, "tool_use_accuracy": 0.7, "resolution": 0.7, '
        '"response_quality": 0.7, "overall": 0.7, "reasoning": "ok"}'
    )
    mock_response = _mock_llm_response(response_json)

    with patch(
        "app.adapters.litellm_judge.litellm.acompletion",
        new_callable=AsyncMock,
        return_value=mock_response,
    ) as mock_completion:
        await adapter.evaluate_conversation(
            messages=_sample_messages(),
            tool_calls=_sample_tool_calls(),
            judge_config=judge_config,
        )

    call_kwargs = mock_completion.call_args[1]
    assert call_kwargs["api_key"] == "sk-test-key"
    assert call_kwargs["api_base"] == "http://localhost:4000"
