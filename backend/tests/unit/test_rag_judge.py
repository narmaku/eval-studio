"""Tests for LiteLLMJudgeAdapter RAG evaluation."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.adapters.base import JudgeConfigParams, Score
from app.adapters.litellm_judge import LiteLLMJudgeAdapter


def _make_adapter(**kwargs) -> LiteLLMJudgeAdapter:
    defaults = {"model": "test-model", "max_concurrency": 5}
    defaults.update(kwargs)
    return LiteLLMJudgeAdapter(**defaults)


def _mock_llm_response(content: str | None) -> MagicMock:
    mock = MagicMock()
    mock.choices = [MagicMock()]
    mock.choices[0].message.content = content
    return mock


def _sample_chunks() -> list[str]:
    return [
        "RHEL stands for Red Hat Enterprise Linux, a commercial Linux distribution.",
        "RHEL provides long-term support and security updates for enterprise environments.",
        "RHEL uses RPM package management and systemd for service management.",
    ]


@pytest.mark.asyncio
async def test_evaluate_rag_success():
    """All 4 metrics returned with scores when no specific metrics requested."""
    adapter = _make_adapter()

    response_json = (
        '{"context_precision": 0.9, "context_recall": 0.85, "faithfulness": 0.95, '
        '"answer_relevance": 0.8, "reasoning": "Good RAG response."}'
    )
    mock_response = _mock_llm_response(response_json)

    with patch(
        "app.adapters.litellm_judge.litellm.acompletion",
        new_callable=AsyncMock,
        return_value=mock_response,
    ):
        result = await adapter.evaluate_rag(
            question="What is RHEL?",
            context_chunks=_sample_chunks(),
            answer="RHEL is Red Hat Enterprise Linux.",
            expected_answer="Red Hat Enterprise Linux",
            metrics=[],
        )

    assert isinstance(result, dict)
    assert len(result) == 4
    for metric_name in ("context_precision", "context_recall", "faithfulness", "answer_relevance"):
        assert metric_name in result
        assert isinstance(result[metric_name], Score)
        assert 0.0 <= result[metric_name].value <= 1.0

    assert result["context_precision"].value == pytest.approx(0.9)
    assert result["context_recall"].value == pytest.approx(0.85)
    assert result["faithfulness"].value == pytest.approx(0.95)
    assert result["answer_relevance"].value == pytest.approx(0.8)
    assert result["context_precision"].reasoning == "Good RAG response."


@pytest.mark.asyncio
async def test_evaluate_rag_specific_metrics():
    """Only requested metrics are returned when metrics param is non-empty."""
    adapter = _make_adapter()

    response_json = (
        '{"context_precision": 0.9, "context_recall": 0.85, "faithfulness": 0.95, '
        '"answer_relevance": 0.8, "reasoning": "Good RAG response."}'
    )
    mock_response = _mock_llm_response(response_json)

    with patch(
        "app.adapters.litellm_judge.litellm.acompletion",
        new_callable=AsyncMock,
        return_value=mock_response,
    ):
        result = await adapter.evaluate_rag(
            question="What is RHEL?",
            context_chunks=_sample_chunks(),
            answer="RHEL is Red Hat Enterprise Linux.",
            expected_answer="Red Hat Enterprise Linux",
            metrics=["faithfulness", "answer_relevance"],
        )

    assert len(result) == 2
    assert "faithfulness" in result
    assert "answer_relevance" in result
    assert "context_precision" not in result
    assert "context_recall" not in result


@pytest.mark.asyncio
async def test_evaluate_rag_empty_chunks():
    """Empty chunks AND no answer returns neutral scores without calling LLM."""
    adapter = _make_adapter()

    with patch(
        "app.adapters.litellm_judge.litellm.acompletion",
        new_callable=AsyncMock,
    ) as mock_completion:
        result = await adapter.evaluate_rag(
            question="What is RHEL?",
            context_chunks=[],
            answer="",
            expected_answer="Red Hat Enterprise Linux",
            metrics=[],
        )

    mock_completion.assert_not_called()
    assert len(result) == 4
    for metric_name in ("context_precision", "context_recall", "faithfulness", "answer_relevance"):
        assert result[metric_name].value == 0.5
        assert result[metric_name].passed is False


@pytest.mark.asyncio
async def test_evaluate_rag_no_expected_answer():
    """When expected_answer is None, context_recall defaults to neutral 0.5."""
    adapter = _make_adapter()

    response_json = (
        '{"context_precision": 0.9, "context_recall": 0.5, "faithfulness": 0.95, '
        '"answer_relevance": 0.8, "reasoning": "No expected answer to compare."}'
    )
    mock_response = _mock_llm_response(response_json)

    with patch(
        "app.adapters.litellm_judge.litellm.acompletion",
        new_callable=AsyncMock,
        return_value=mock_response,
    ):
        result = await adapter.evaluate_rag(
            question="What is RHEL?",
            context_chunks=_sample_chunks(),
            answer="RHEL is Red Hat Enterprise Linux.",
            expected_answer=None,
            metrics=[],
        )

    assert len(result) == 4
    # context_recall should be forced to neutral when no expected_answer
    assert result["context_recall"].value == 0.5
    assert result["context_recall"].reasoning is not None
    assert "expected" in result["context_recall"].reasoning.lower()
    # Other metrics should come from LLM
    assert result["context_precision"].value == pytest.approx(0.9)
    assert result["faithfulness"].value == pytest.approx(0.95)
    assert result["answer_relevance"].value == pytest.approx(0.8)


@pytest.mark.asyncio
async def test_evaluate_rag_parse_error():
    """Invalid JSON from LLM returns fallback scores of 0.0."""
    adapter = _make_adapter()

    mock_response = _mock_llm_response("This is not valid JSON at all")

    with patch(
        "app.adapters.litellm_judge.litellm.acompletion",
        new_callable=AsyncMock,
        return_value=mock_response,
    ):
        result = await adapter.evaluate_rag(
            question="What is RHEL?",
            context_chunks=_sample_chunks(),
            answer="RHEL is Red Hat Enterprise Linux.",
            expected_answer="Red Hat Enterprise Linux",
            metrics=[],
        )

    assert len(result) == 4
    for metric_name in ("context_precision", "context_recall", "faithfulness", "answer_relevance"):
        assert result[metric_name].value == 0.0
        assert result[metric_name].passed is False
        assert "unparseable" in result[metric_name].reasoning


@pytest.mark.asyncio
async def test_evaluate_rag_truncation():
    """More than 20 chunks are truncated with a notice."""
    adapter = _make_adapter()

    chunks = [f"Chunk content number {i}" for i in range(25)]

    response_json = (
        '{"context_precision": 0.7, "context_recall": 0.7, "faithfulness": 0.7, '
        '"answer_relevance": 0.7, "reasoning": "Truncated chunks."}'
    )
    mock_response = _mock_llm_response(response_json)

    with patch(
        "app.adapters.litellm_judge.litellm.acompletion",
        new_callable=AsyncMock,
        return_value=mock_response,
    ) as mock_completion:
        await adapter.evaluate_rag(
            question="What is RHEL?",
            context_chunks=chunks,
            answer="RHEL is Red Hat Enterprise Linux.",
            expected_answer="Red Hat Enterprise Linux",
            metrics=[],
        )

    mock_completion.assert_called_once()
    call_kwargs = mock_completion.call_args[1]
    prompt_content = call_kwargs["messages"][0]["content"]
    # Should contain truncation notice
    assert "5 additional chunks omitted" in prompt_content
    # Should contain [Chunk 1] and [Chunk 20] but not [Chunk 21]
    assert "[Chunk 1]" in prompt_content
    assert "[Chunk 20]" in prompt_content
    assert "[Chunk 21]" not in prompt_content


@pytest.mark.asyncio
async def test_evaluate_rag_api_key_and_base():
    """api_key and api_base are forwarded to LiteLLM when set."""
    adapter = _make_adapter(api_key="sk-test-key", api_base="http://localhost:4000")

    response_json = (
        '{"context_precision": 0.7, "context_recall": 0.7, "faithfulness": 0.7, '
        '"answer_relevance": 0.7, "reasoning": "ok"}'
    )
    mock_response = _mock_llm_response(response_json)

    with patch(
        "app.adapters.litellm_judge.litellm.acompletion",
        new_callable=AsyncMock,
        return_value=mock_response,
    ) as mock_completion:
        await adapter.evaluate_rag(
            question="What is RHEL?",
            context_chunks=_sample_chunks(),
            answer="RHEL is Red Hat Enterprise Linux.",
            expected_answer="Red Hat Enterprise Linux",
            metrics=[],
        )

    call_kwargs = mock_completion.call_args[1]
    assert call_kwargs["api_key"] == "sk-test-key"
    assert call_kwargs["api_base"] == "http://localhost:4000"


@pytest.mark.asyncio
async def test_evaluate_rag_none_content():
    """LLM returns None content -- returns fallback Score(0.0) for all metrics."""
    adapter = _make_adapter()

    mock_response = _mock_llm_response(None)

    with patch(
        "app.adapters.litellm_judge.litellm.acompletion",
        new_callable=AsyncMock,
        return_value=mock_response,
    ):
        result = await adapter.evaluate_rag(
            question="What is RHEL?",
            context_chunks=_sample_chunks(),
            answer="RHEL is Red Hat Enterprise Linux.",
            expected_answer="Red Hat Enterprise Linux",
            metrics=[],
        )

    assert len(result) == 4
    for metric_name in ("context_precision", "context_recall", "faithfulness", "answer_relevance"):
        assert result[metric_name].value == 0.0
        assert result[metric_name].passed is False
        assert "empty" in result[metric_name].reasoning


@pytest.mark.asyncio
async def test_evaluate_rag_custom_threshold():
    """judge_config.pass_threshold=0.5 makes score 0.6 pass (would fail with default 0.7)."""
    adapter = _make_adapter()
    judge_config = JudgeConfigParams(pass_threshold=0.5, temperature=0.3)

    response_json = (
        '{"context_precision": 0.6, "context_recall": 0.6, "faithfulness": 0.6, '
        '"answer_relevance": 0.6, "reasoning": "Moderate scores."}'
    )
    mock_response = _mock_llm_response(response_json)

    with patch(
        "app.adapters.litellm_judge.litellm.acompletion",
        new_callable=AsyncMock,
        return_value=mock_response,
    ) as mock_completion:
        result = await adapter.evaluate_rag(
            question="What is RHEL?",
            context_chunks=_sample_chunks(),
            answer="RHEL is Red Hat Enterprise Linux.",
            expected_answer="Red Hat Enterprise Linux",
            metrics=[],
            judge_config=judge_config,
        )

    for metric in ("context_precision", "faithfulness", "answer_relevance"):
        assert result[metric].passed is True, f"{metric} should pass with threshold 0.5"
        assert result[metric].value == pytest.approx(0.6)

    call_kwargs = mock_completion.call_args[1]
    assert call_kwargs["temperature"] == 0.3


@pytest.mark.asyncio
async def test_format_chunks_basic():
    """_format_chunks produces numbered chunk format."""
    chunks = ["First chunk", "Second chunk", "Third chunk"]
    result = LiteLLMJudgeAdapter._format_chunks(chunks)
    assert "[Chunk 1] First chunk" in result
    assert "[Chunk 2] Second chunk" in result
    assert "[Chunk 3] Third chunk" in result


@pytest.mark.asyncio
async def test_format_chunks_truncation():
    """_format_chunks truncates to 20 and adds notice."""
    chunks = [f"Chunk content {i}" for i in range(30)]
    result = LiteLLMJudgeAdapter._format_chunks(chunks)
    assert "[Chunk 1]" in result
    assert "[Chunk 20]" in result
    assert "[Chunk 21]" not in result
    assert "10 additional chunks omitted" in result


@pytest.mark.asyncio
async def test_format_chunks_empty():
    """_format_chunks handles empty list."""
    result = LiteLLMJudgeAdapter._format_chunks([])
    assert result == ""
