from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.adapters.base import JudgeConfigParams
from app.adapters.litellm_judge import LiteLLMJudgeAdapter


@pytest.mark.asyncio
async def test_litellm_adapter_evaluate_qa():
    adapter = LiteLLMJudgeAdapter(model="test-model", max_concurrency=5)
    judge_config = JudgeConfigParams(
        model="test-model",
        temperature=0.0,
        prompt_template=None,
        pass_threshold=0.7,
    )

    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message.content = '{"score": 0.85, "reasoning": "Good answer"}'

    with patch(
        "app.adapters.litellm_judge.litellm.acompletion",
        new_callable=AsyncMock,
        return_value=mock_response,
    ):
        score = await adapter.evaluate_qa(
            question="What is RHEL?",
            expected_answer="Red Hat Enterprise Linux",
            actual_answer="RHEL is Red Hat Enterprise Linux, a commercial Linux distribution.",
            judge_config=judge_config,
        )
        assert score.value == 0.85
        assert score.passed is True  # 0.85 >= 0.7 threshold
        assert score.reasoning == "Good answer"


@pytest.mark.asyncio
async def test_litellm_adapter_evaluate_qa_failing_score():
    adapter = LiteLLMJudgeAdapter(model="test-model", max_concurrency=5)
    judge_config = JudgeConfigParams(
        model="test-model",
        temperature=0.0,
        prompt_template=None,
        pass_threshold=0.7,
    )

    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message.content = '{"score": 0.3, "reasoning": "Incorrect answer"}'

    with patch(
        "app.adapters.litellm_judge.litellm.acompletion",
        new_callable=AsyncMock,
        return_value=mock_response,
    ):
        score = await adapter.evaluate_qa(
            question="What is RHEL?",
            expected_answer="Red Hat Enterprise Linux",
            actual_answer="RHEL is a web framework.",
            judge_config=judge_config,
        )
        assert score.value == 0.3
        assert score.passed is False  # 0.3 < 0.7 threshold
        assert score.reasoning == "Incorrect answer"


@pytest.mark.asyncio
async def test_litellm_adapter_evaluate_qa_invalid_json():
    """Test that the adapter returns a zero score with reasoning when the LLM returns invalid JSON."""
    adapter = LiteLLMJudgeAdapter(model="test-model", max_concurrency=5)
    judge_config = JudgeConfigParams(
        model="test-model",
        temperature=0.0,
        prompt_template=None,
        pass_threshold=0.7,
    )

    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message.content = "This is not valid JSON at all"

    with patch(
        "app.adapters.litellm_judge.litellm.acompletion",
        new_callable=AsyncMock,
        return_value=mock_response,
    ):
        score = await adapter.evaluate_qa(
            question="What is RHEL?",
            expected_answer="Red Hat Enterprise Linux",
            actual_answer="Something",
            judge_config=judge_config,
        )
        assert score.value == 0.0
        assert score.passed is False
        assert "unparseable" in score.reasoning


@pytest.mark.asyncio
async def test_litellm_adapter_evaluate_qa_none_content():
    """Test that the adapter returns a zero score when the LLM returns None content."""
    adapter = LiteLLMJudgeAdapter(model="test-model", max_concurrency=5)
    judge_config = JudgeConfigParams(
        model="test-model",
        temperature=0.0,
        prompt_template=None,
        pass_threshold=0.7,
    )

    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message.content = None

    with patch(
        "app.adapters.litellm_judge.litellm.acompletion",
        new_callable=AsyncMock,
        return_value=mock_response,
    ):
        score = await adapter.evaluate_qa(
            question="What is RHEL?",
            expected_answer="Red Hat Enterprise Linux",
            actual_answer="Something",
            judge_config=judge_config,
        )
        assert score.value == 0.0
        assert score.passed is False
        assert "empty" in score.reasoning


@pytest.mark.asyncio
async def test_extra_params_do_not_override_explicit_kwargs():
    """extra_params must not clobber model/temperature/response_format."""
    adapter = LiteLLMJudgeAdapter(
        model="judge-model",
        extra_params={"model": "should-not-win", "temperature": 99.0},
    )
    judge_config = JudgeConfigParams(model="judge-model", temperature=0.5, pass_threshold=0.7)

    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message.content = '{"score": 0.9, "reasoning": "ok"}'

    with patch(
        "app.adapters.litellm_judge.litellm.acompletion",
        new_callable=AsyncMock,
        return_value=mock_response,
    ) as mock_call:
        await adapter.evaluate_qa(question="q", expected_answer="a", actual_answer="a", judge_config=judge_config)
        kwargs = mock_call.call_args.kwargs
        assert kwargs["model"] == "judge-model"
        assert kwargs["temperature"] == 0.5


@pytest.mark.asyncio
async def test_litellm_client_used_for_proxy_ssl():
    """get_litellm_client is called with adapter's proxy/SSL settings."""
    adapter = LiteLLMJudgeAdapter(
        model="judge-model",
        api_key="key-1",
        proxy="http://proxy:8080",
        ssl_cert_path="/tmp/ca.pem",
    )
    judge_config = JudgeConfigParams(model="judge-model", temperature=0.0, pass_threshold=0.7)

    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message.content = '{"score": 0.9, "reasoning": "ok"}'

    sentinel_client = MagicMock()

    with (
        patch(
            "app.adapters.litellm_judge.litellm.acompletion",
            new_callable=AsyncMock,
            return_value=mock_response,
        ) as mock_acompletion,
        patch(
            "app.adapters.litellm_judge.get_litellm_client",
            return_value=sentinel_client,
        ) as mock_get_client,
    ):
        await adapter.evaluate_qa(question="q", expected_answer="a", actual_answer="a", judge_config=judge_config)
        mock_get_client.assert_called_once_with("http://proxy:8080", "/tmp/ca.pem", None, "key-1", None)
        assert mock_acompletion.call_args.kwargs.get("client") is sentinel_client
