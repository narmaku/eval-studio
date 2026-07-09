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


class TestDimensionBasedQAScoring:
    """Tests for evaluate_qa with rubric dimensions."""

    @pytest.mark.asyncio
    async def test_dimensions_produce_weighted_score_and_breakdown(self):
        adapter = LiteLLMJudgeAdapter(model="test-model", max_concurrency=5)
        dims = [
            {"name": "accuracy", "weight": 2.0, "description": "Factual accuracy"},
            {"name": "completeness", "weight": 1.0, "description": "Coverage of key points"},
        ]
        judge_config = JudgeConfigParams(
            model="test-model",
            temperature=0.0,
            pass_threshold=0.7,
            dimensions=dims,
        )

        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[
            0
        ].message.content = '{"accuracy": 0.9, "completeness": 0.6, "reasoning": "Good but incomplete"}'

        with patch(
            "app.adapters.litellm_judge.litellm.acompletion",
            new_callable=AsyncMock,
            return_value=mock_response,
        ):
            score = await adapter.evaluate_qa(
                question="What is RHEL?",
                expected_answer="Red Hat Enterprise Linux",
                actual_answer="RHEL is a Linux distro.",
                judge_config=judge_config,
            )
            # Weighted average: (0.9*2 + 0.6*1) / (2+1) = 2.4/3 = 0.8
            assert abs(score.value - 0.8) < 1e-6
            assert score.passed is True  # 0.8 >= 0.7
            assert score.breakdown == {"accuracy": 0.9, "completeness": 0.6}
            assert score.reasoning == "Good but incomplete"

    @pytest.mark.asyncio
    async def test_dimensions_failing_threshold(self):
        adapter = LiteLLMJudgeAdapter(model="test-model", max_concurrency=5)
        dims = [
            {"name": "accuracy", "weight": 1.0, "description": "Factual accuracy"},
            {"name": "clarity", "weight": 1.0, "description": "Clarity of response"},
        ]
        judge_config = JudgeConfigParams(
            model="test-model",
            temperature=0.0,
            pass_threshold=0.8,
            dimensions=dims,
        )

        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = '{"accuracy": 0.5, "clarity": 0.7, "reasoning": "Poor accuracy"}'

        with patch(
            "app.adapters.litellm_judge.litellm.acompletion",
            new_callable=AsyncMock,
            return_value=mock_response,
        ):
            score = await adapter.evaluate_qa(
                question="q",
                expected_answer="a",
                actual_answer="a",
                judge_config=judge_config,
            )
            # Average: (0.5 + 0.7) / 2 = 0.6
            assert abs(score.value - 0.6) < 1e-6
            assert score.passed is False  # 0.6 < 0.8

    @pytest.mark.asyncio
    async def test_dimensions_empty_falls_through_to_default(self):
        """Empty dimensions list uses single-score default path."""
        adapter = LiteLLMJudgeAdapter(model="test-model", max_concurrency=5)
        judge_config = JudgeConfigParams(
            model="test-model",
            temperature=0.0,
            pass_threshold=0.7,
            dimensions=[],
        )

        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = '{"score": 0.85, "reasoning": "Good"}'

        with patch(
            "app.adapters.litellm_judge.litellm.acompletion",
            new_callable=AsyncMock,
            return_value=mock_response,
        ):
            score = await adapter.evaluate_qa(
                question="q",
                expected_answer="a",
                actual_answer="a",
                judge_config=judge_config,
            )
            assert score.value == 0.85
            assert score.breakdown is None

    @pytest.mark.asyncio
    async def test_dimensions_llm_empty_response(self):
        adapter = LiteLLMJudgeAdapter(model="test-model", max_concurrency=5)
        judge_config = JudgeConfigParams(
            model="test-model",
            dimensions=[{"name": "accuracy", "weight": 1.0, "description": "test"}],
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
                question="q",
                expected_answer="a",
                actual_answer="a",
                judge_config=judge_config,
            )
            assert score.value == 0.0
            assert score.passed is False


class TestBuildDimensionsPrompt:
    """Tests for the _build_dimensions_prompt static method."""

    def test_builds_section_and_schema(self):
        dims = [
            {"name": "accuracy", "weight": 2.0, "description": "Factual accuracy"},
            {"name": "clarity", "weight": 1.0, "description": "Clarity of response"},
        ]
        section, schema, names = LiteLLMJudgeAdapter._build_dimensions_prompt(dims)
        assert "**accuracy**" in section
        assert "weight=2.0" in section
        assert '"accuracy": <float>' in schema
        assert '"clarity": <float>' in schema
        assert names == ["accuracy", "clarity"]

    def test_single_dimension(self):
        dims = [{"name": "overall", "weight": 1.0, "description": "Overall quality"}]
        section, _schema, names = LiteLLMJudgeAdapter._build_dimensions_prompt(dims)
        assert "**overall**" in section
        assert names == ["overall"]

    def test_build_dimensions_prompt_with_criteria(self):
        """Criteria sub-items are listed under each dimension."""
        dims = [
            {
                "name": "factual_correctness",
                "weight": 0.6,
                "description": "Evaluates factual accuracy.",
                "criteria": [
                    {"name": "identifies_catalog", "criterion": "Must identify the catalog.", "weight": 3},
                    {"name": "covers_certification", "criterion": "Must mention certification.", "weight": 2},
                ],
            },
            {
                "name": "completeness",
                "weight": 0.4,
                "description": "Evaluates completeness.",
            },
        ]
        section, _schema, _names = LiteLLMJudgeAdapter._build_dimensions_prompt(dims)
        # Criteria should appear under the first dimension
        assert "Criteria:" in section
        assert "identifies_catalog" in section
        assert "weight 3" in section
        assert "Must identify the catalog." in section
        assert "covers_certification" in section
        # Second dimension without criteria should not have "Criteria:" after it
        lines = section.split("\n")
        completeness_idx = next(i for i, line in enumerate(lines) if "completeness" in line)
        # No Criteria: line after completeness
        remaining = "\n".join(lines[completeness_idx + 1 :])
        assert "Criteria:" not in remaining

    def test_build_dimensions_prompt_without_criteria(self):
        """Dimensions without criteria produce the same output as before."""
        dims = [
            {"name": "accuracy", "weight": 1.0, "description": "Factual accuracy"},
        ]
        section, _schema, names = LiteLLMJudgeAdapter._build_dimensions_prompt(dims)
        assert "Criteria:" not in section
        assert "**accuracy**" in section
        assert names == ["accuracy"]

    def test_build_dimensions_prompt_empty_criteria_list(self):
        """Empty criteria list treated same as no criteria."""
        dims = [
            {"name": "accuracy", "weight": 1.0, "description": "Factual accuracy", "criteria": []},
        ]
        section, _schema, _names = LiteLLMJudgeAdapter._build_dimensions_prompt(dims)
        assert "Criteria:" not in section

    def test_build_dimensions_prompt_criteria_none(self):
        """Criteria set to None treated same as absent."""
        dims = [
            {"name": "accuracy", "weight": 1.0, "description": "Factual accuracy", "criteria": None},
        ]
        section, _schema, _names = LiteLLMJudgeAdapter._build_dimensions_prompt(dims)
        assert "Criteria:" not in section


class TestParseJsonLenient:
    """Tests for _parse_json_lenient markdown fence stripping."""

    def test_plain_json(self):
        result = LiteLLMJudgeAdapter._parse_json_lenient('{"score": 0.8}')
        assert result == {"score": 0.8}

    def test_markdown_fenced_json(self):
        content = '```json\n{"score": 0.8, "reasoning": "good"}\n```'
        result = LiteLLMJudgeAdapter._parse_json_lenient(content)
        assert result == {"score": 0.8, "reasoning": "good"}

    def test_markdown_fenced_no_lang(self):
        content = '```\n{"score": 0.5}\n```'
        result = LiteLLMJudgeAdapter._parse_json_lenient(content)
        assert result == {"score": 0.5}

    def test_invalid_content(self):
        assert LiteLLMJudgeAdapter._parse_json_lenient("not json at all") is None


class TestAskJudgeRetry:
    """Tests for _ask_judge retry + error handling."""

    @pytest.mark.asyncio
    async def test_retries_on_parse_failure(self):
        adapter = LiteLLMJudgeAdapter(model="test-model")
        judge_config = JudgeConfigParams(model="test-model", pass_threshold=0.7)

        bad_response = MagicMock()
        bad_response.choices = [MagicMock()]
        bad_response.choices[0].message.content = "not json"

        good_response = MagicMock()
        good_response.choices = [MagicMock()]
        good_response.choices[0].message.content = '{"score": 0.9, "reasoning": "ok"}'

        with patch(
            "app.adapters.litellm_judge.litellm.acompletion",
            new_callable=AsyncMock,
            side_effect=[bad_response, good_response],
        ):
            result = await adapter._ask_judge("test prompt", judge_config, "qa")
            assert result == {"score": 0.9, "reasoning": "ok"}

    @pytest.mark.asyncio
    async def test_retries_on_api_error(self):
        adapter = LiteLLMJudgeAdapter(model="test-model")
        judge_config = JudgeConfigParams(model="test-model", pass_threshold=0.7)

        good_response = MagicMock()
        good_response.choices = [MagicMock()]
        good_response.choices[0].message.content = '{"score": 0.7}'

        with patch(
            "app.adapters.litellm_judge.litellm.acompletion",
            new_callable=AsyncMock,
            side_effect=[Exception("rate limited"), good_response],
        ):
            result = await adapter._ask_judge("test prompt", judge_config, "qa")
            assert result == {"score": 0.7}

    @pytest.mark.asyncio
    async def test_returns_none_after_exhausting_retries(self):
        adapter = LiteLLMJudgeAdapter(model="test-model")
        judge_config = JudgeConfigParams(model="test-model", pass_threshold=0.7)

        with patch(
            "app.adapters.litellm_judge.litellm.acompletion",
            new_callable=AsyncMock,
            side_effect=Exception("persistent error"),
        ):
            result = await adapter._ask_judge("test prompt", judge_config, "qa")
            assert result is None
