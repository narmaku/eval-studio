"""Unit tests for rubric service (import, generate, refine)."""

import textwrap
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.rubric_service import (
    clean_yaml_block,
    convert_rubric_kit_to_internal,
    generate_rubric,
    parse_rubric_yaml,
    refine_rubric,
)


class TestCleanYamlBlock:
    """Tests for stripping markdown code fences from YAML."""

    def test_plain_yaml_unchanged(self):
        yaml_text = "name: test\nvalue: 1"
        assert clean_yaml_block(yaml_text) == yaml_text

    def test_strips_yaml_code_fence(self):
        text = "```yaml\nname: test\nvalue: 1\n```"
        assert clean_yaml_block(text) == "name: test\nvalue: 1"

    def test_strips_generic_code_fence(self):
        text = "```\nname: test\n```"
        assert clean_yaml_block(text) == "name: test"

    def test_strips_leading_whitespace(self):
        text = "  ```yaml\n  name: test\n  ```  "
        result = clean_yaml_block(text)
        assert "name: test" in result

    def test_empty_string(self):
        assert clean_yaml_block("") == ""


class TestParseRubricYaml:
    """Tests for parsing rubric YAML content into internal format."""

    def test_nested_rubric_key(self):
        yaml_content = textwrap.dedent("""\
            rubric:
              name: "Test Rubric"
              description: "A test"
              dimensions:
                - name: accuracy
                  weight: 0.6
                  description: "How accurate"
                - name: completeness
                  weight: 0.4
                  description: "How complete"
              pass_threshold: 0.8
              aggregation: weighted_average
        """)
        result = parse_rubric_yaml(yaml_content)
        assert result["name"] == "Test Rubric"
        assert result["description"] == "A test"
        assert len(result["dimensions"]) == 2
        assert result["dimensions"][0]["name"] == "accuracy"
        assert result["dimensions"][0]["weight"] == 0.6
        assert result["pass_threshold"] == 0.8
        assert result["aggregation"] == "weighted_average"

    def test_flat_format(self):
        yaml_content = textwrap.dedent("""\
            name: "Flat Rubric"
            dimensions:
              - name: quality
                weight: 1.0
                description: "Overall quality"
        """)
        result = parse_rubric_yaml(yaml_content)
        assert result["name"] == "Flat Rubric"
        assert len(result["dimensions"]) == 1

    def test_defaults_applied(self):
        yaml_content = textwrap.dedent("""\
            dimensions:
              - name: quality
                weight: 1.0
                description: "Overall quality"
        """)
        result = parse_rubric_yaml(yaml_content)
        assert result["name"] == "Imported Rubric"
        assert result["pass_threshold"] == 0.7
        assert result["aggregation"] == "weighted_average"
        assert result["description"] is None

    def test_dimensions_without_weight_get_default(self):
        yaml_content = textwrap.dedent("""\
            dimensions:
              - name: quality
                description: "Overall quality"
        """)
        result = parse_rubric_yaml(yaml_content)
        assert result["dimensions"][0]["weight"] == 1.0

    def test_dimensions_without_description_get_default(self):
        yaml_content = textwrap.dedent("""\
            dimensions:
              - name: quality
                weight: 0.5
        """)
        result = parse_rubric_yaml(yaml_content)
        assert result["dimensions"][0]["description"] == "quality"

    def test_invalid_yaml_raises(self):
        with pytest.raises(ValueError, match="Invalid YAML"):
            parse_rubric_yaml("::invalid: yaml: [")

    def test_empty_yaml_raises(self):
        with pytest.raises(ValueError, match="No dimensions"):
            parse_rubric_yaml("")

    def test_no_dimensions_raises(self):
        yaml_content = "name: No Dims"
        with pytest.raises(ValueError, match="No dimensions"):
            parse_rubric_yaml(yaml_content)

    def test_prompt_template_included(self):
        yaml_content = textwrap.dedent("""\
            name: "Prompted"
            prompt_template: "Rate: {response}"
            dimensions:
              - name: q
                weight: 1.0
                description: "q"
        """)
        result = parse_rubric_yaml(yaml_content)
        assert result["prompt_template"] == "Rate: {response}"

    def test_rubric_kit_format_with_criteria(self):
        """Test parsing rubric-kit native format with dimensions and criteria."""
        yaml_content = textwrap.dedent("""\
            dimensions:
              - name: correctness
                description: "Factual accuracy"
                grading_type: score
                scores:
                  1: "Incorrect"
                  3: "Partially correct"
                  5: "Fully correct"
              - name: completeness
                description: "Answer completeness"
                grading_type: binary
            criteria:
              - name: "factual_accuracy"
                category: "accuracy"
                weight: 3
                dimension: correctness
                criterion: "Is the answer factually correct?"
              - name: "full_coverage"
                category: "coverage"
                weight: 2
                dimension: completeness
                criterion: "Does the answer cover all aspects?"
        """)
        result = parse_rubric_yaml(yaml_content)
        assert len(result["dimensions"]) == 2
        assert result["dimensions"][0]["name"] == "correctness"
        assert result["dimensions"][0]["description"] == "Factual accuracy"
        # Weights derived from criteria
        assert result["dimensions"][0]["weight"] > 0
        assert result["dimensions"][1]["weight"] > 0


class TestConvertRubricKitToInternal:
    """Tests for converting rubric-kit Rubric objects to internal format."""

    def test_basic_conversion(self):
        from rubric_kit import Criterion, Dimension, Rubric

        rubric = Rubric(
            dimensions=[
                Dimension(
                    name="accuracy",
                    description="Factual accuracy",
                    grading_type="score",
                    scores={1: "Bad", 5: "Good"},
                ),
            ],
            criteria=[
                Criterion(
                    name="fact_check",
                    weight=3,
                    dimension="accuracy",
                    criterion="Is it factually correct?",
                ),
            ],
        )
        result = convert_rubric_kit_to_internal(rubric)
        assert len(result["dimensions"]) == 1
        assert result["dimensions"][0]["name"] == "accuracy"
        assert result["dimensions"][0]["description"] == "Factual accuracy"
        assert result["dimensions"][0]["weight"] > 0
        assert result["pass_threshold"] == 0.7
        assert result["aggregation"] == "weighted_average"

    def test_multiple_dimensions_weight_distribution(self):
        from rubric_kit import Criterion, Dimension, Rubric

        rubric = Rubric(
            dimensions=[
                Dimension(name="d1", description="dim1", grading_type="score", scores={1: "Bad", 5: "Good"}),
                Dimension(name="d2", description="dim2", grading_type="binary"),
            ],
            criteria=[
                Criterion(name="c1", weight=3, dimension="d1", criterion="c1?"),
                Criterion(name="c2", weight=1, dimension="d2", criterion="c2?"),
            ],
        )
        result = convert_rubric_kit_to_internal(rubric)
        assert len(result["dimensions"]) == 2
        total_weight = sum(d["weight"] for d in result["dimensions"])
        assert abs(total_weight - 1.0) < 0.01


class TestGenerateRubric:
    """Tests for rubric generation via rubric-kit + LLM."""

    @patch("app.services.rubric_service.rubric_kit_generate")
    def test_generate_calls_rubric_kit(self, mock_generate):
        from rubric_kit import Criterion, Dimension, GenerationResult, Rubric

        mock_rubric = Rubric(
            dimensions=[
                Dimension(name="quality", description="Quality", grading_type="score", scores={1: "Bad", 5: "Good"}),
            ],
            criteria=[
                Criterion(name="q1", weight=3, dimension="quality", criterion="Is it good?"),
            ],
        )
        mock_generate.return_value = GenerationResult(
            rubric=mock_rubric,
            model="test-model",
            input_type="qna",
            input_source="<in-memory>",
        )

        result = generate_rubric(
            description="Test description",
            sample_data=None,
            model="test-model",
            api_base=None,
        )

        mock_generate.assert_called_once()
        assert len(result["dimensions"]) == 1
        assert result["dimensions"][0]["name"] == "quality"

    @patch("app.services.rubric_service.rubric_kit_generate")
    def test_generate_with_sample_data(self, mock_generate):
        from rubric_kit import Criterion, Dimension, GenerationResult, Rubric

        mock_rubric = Rubric(
            dimensions=[
                Dimension(name="quality", description="Quality", grading_type="score", scores={1: "Bad", 5: "Good"}),
            ],
            criteria=[
                Criterion(name="q1", weight=3, dimension="quality", criterion="Is it good?"),
            ],
        )
        mock_generate.return_value = GenerationResult(
            rubric=mock_rubric,
            model="test-model",
            input_type="qna",
            input_source="<in-memory>",
        )

        result = generate_rubric(
            description="Test description",
            sample_data="Q: What? A: This.",
            model="test-model",
            api_base="http://localhost:8080",
        )

        call_kwargs = mock_generate.call_args[1]
        assert "Test description" in call_kwargs["input_content"]
        assert "What?" in call_kwargs["input_content"]
        assert call_kwargs["base_url"] == "http://localhost:8080"

    @patch("app.services.rubric_service.rubric_kit_generate")
    def test_generate_propagates_error(self, mock_generate):
        mock_generate.side_effect = Exception("LLM call failed")

        with pytest.raises(Exception, match="LLM call failed"):
            generate_rubric(
                description="Test",
                sample_data=None,
                model="test-model",
                api_base=None,
            )


class TestRefineRubric:
    """Tests for rubric refinement via rubric-kit + LLM."""

    @patch("app.services.rubric_service.rubric_kit_refine")
    def test_refine_calls_rubric_kit(self, mock_refine):
        from rubric_kit import Criterion, Dimension, RefinementResult, Rubric

        mock_rubric = Rubric(
            dimensions=[
                Dimension(name="quality", description="Improved quality", grading_type="score", scores={1: "1", 5: "5"}),
            ],
            criteria=[
                Criterion(name="q1", weight=3, dimension="quality", criterion="Is it good?"),
            ],
        )
        mock_refine.return_value = RefinementResult(
            rubric=mock_rubric,
            original_rubric=mock_rubric,
            model="test-model",
            had_feedback=True,
        )

        existing_rubric = {
            "name": "Old Rubric",
            "description": "Old desc",
            "dimensions": [{"name": "quality", "weight": 1.0, "description": "Quality"}],
            "pass_threshold": 0.7,
            "aggregation": "weighted_average",
            "prompt_template": None,
        }

        result = refine_rubric(
            existing_rubric=existing_rubric,
            feedback="Add more dimensions",
            model="test-model",
            api_base=None,
        )

        mock_refine.assert_called_once()
        assert len(result["dimensions"]) == 1
        assert result["dimensions"][0]["name"] == "quality"

    @patch("app.services.rubric_service.rubric_kit_refine")
    def test_refine_preserves_metadata(self, mock_refine):
        from rubric_kit import Criterion, Dimension, RefinementResult, Rubric

        mock_rubric = Rubric(
            dimensions=[
                Dimension(name="quality", description="Quality", grading_type="score", scores={1: "1", 5: "5"}),
            ],
            criteria=[
                Criterion(name="q1", weight=3, dimension="quality", criterion="Is it good?"),
            ],
        )
        mock_refine.return_value = RefinementResult(
            rubric=mock_rubric,
            original_rubric=mock_rubric,
            model="test-model",
            had_feedback=True,
        )

        existing_rubric = {
            "name": "My Rubric",
            "description": "My desc",
            "dimensions": [{"name": "quality", "weight": 1.0, "description": "Quality"}],
            "pass_threshold": 0.85,
            "aggregation": "simple_average",
            "prompt_template": "Rate: {response}",
        }

        result = refine_rubric(
            existing_rubric=existing_rubric,
            feedback="Improve it",
            model="test-model",
            api_base=None,
        )

        # Should keep existing name, description, threshold, aggregation, template
        assert result["name"] == "My Rubric"
        assert result["description"] == "My desc"
        assert result["pass_threshold"] == 0.85
        assert result["aggregation"] == "simple_average"
        assert result["prompt_template"] == "Rate: {response}"
