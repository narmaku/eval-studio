"""Unit tests for rubric service (import, generate, refine)."""

import os
import textwrap
from unittest.mock import patch

import pytest
from pydantic import ValidationError

from app.schemas.rubric import RubricCriterion, RubricDimension
from app.services.rubric_service import (
    _substitute_variables,
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

    def test_yaml_wrapped_in_code_fence(self):
        """parse_rubric_yaml strips markdown code fences before parsing."""
        yaml_content = textwrap.dedent("""\
            ```yaml
            name: "Fenced Rubric"
            dimensions:
              - name: quality
                weight: 1.0
                description: "Quality"
            ```""")
        result = parse_rubric_yaml(yaml_content)
        assert result["name"] == "Fenced Rubric"
        assert len(result["dimensions"]) == 1

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
    def test_generate_sets_api_key_env(self, mock_generate, monkeypatch):
        """api_key is set as LITELLM_API_KEY during the rubric-kit call."""
        from rubric_kit import Criterion, Dimension, GenerationResult, Rubric

        monkeypatch.delenv("LITELLM_API_KEY", raising=False)
        captured_key = {}

        def _capture_and_return(**kwargs):
            captured_key["value"] = os.environ.get("LITELLM_API_KEY")
            return GenerationResult(
                rubric=Rubric(
                    dimensions=[
                        Dimension(name="q", description="q", grading_type="score", scores={1: "1", 5: "5"}),
                    ],
                    criteria=[Criterion(name="c", weight=1, dimension="q", criterion="?")],
                ),
                model="m",
                input_type="qna",
                input_source="<in-memory>",
            )

        mock_generate.side_effect = _capture_and_return

        generate_rubric(description="Test", sample_data=None, model="m", api_base=None, api_key="sk-test-123")

        assert captured_key["value"] == "sk-test-123"
        assert os.environ.get("LITELLM_API_KEY") is None

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

        generate_rubric(
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
                Dimension(
                    name="quality", description="Improved quality", grading_type="score", scores={1: "1", 5: "5"}
                ),
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


class TestRubricCriterionSchema:
    """Tests for the RubricCriterion and updated RubricDimension schemas."""

    def test_rubric_criterion_defaults(self):
        c = RubricCriterion(name="test", criterion="some criterion text")
        assert c.name == "test"
        assert c.criterion == "some criterion text"
        assert c.weight == 1.0

    def test_rubric_criterion_custom_weight(self):
        c = RubricCriterion(name="test", criterion="text", weight=3.0)
        assert c.weight == 3.0

    def test_rubric_dimension_criteria_optional(self):
        d = RubricDimension(name="accuracy", weight=1.0, description="test")
        assert d.criteria is None

    def test_rubric_dimension_with_criteria(self):
        d = RubricDimension(
            name="accuracy",
            weight=1.0,
            description="test",
            criteria=[
                RubricCriterion(name="c1", criterion="criterion 1", weight=2.0),
                RubricCriterion(name="c2", criterion="criterion 2"),
            ],
        )
        assert len(d.criteria) == 2
        assert d.criteria[0].name == "c1"
        assert d.criteria[0].weight == 2.0
        assert d.criteria[1].weight == 1.0


class TestRubricKitCriteriaImport:
    """Tests for rubric-kit YAML import with criteria stored per dimension."""

    def test_rubric_kit_format_stores_criteria_per_dimension(self):
        yaml_content = textwrap.dedent("""\
            dimensions:
              - factual_correctness: "Evaluates factual accuracy"
                grading_type: score
                scores:
                  1: "Incorrect"
                  5: "Correct"
              - completeness: "Evaluates answer completeness"
                grading_type: score
                scores:
                  1: "Incomplete"
                  5: "Complete"
            criteria:
              - name: identifies_catalog
                weight: 3
                dimension: factual_correctness
                criterion: "The answer must identify the Red Hat Ecosystem Catalog."
              - name: covers_certification
                weight: 2
                dimension: completeness
                criterion: "The answer must mention RHEL certification."
        """)
        result = parse_rubric_yaml(yaml_content)
        dims = result["dimensions"]

        # factual_correctness should have 1 criterion
        fc_dim = next(d for d in dims if d["name"] == "factual_correctness")
        assert fc_dim["criteria"] is not None
        assert len(fc_dim["criteria"]) == 1
        assert fc_dim["criteria"][0]["name"] == "identifies_catalog"
        assert fc_dim["criteria"][0]["weight"] == 3
        assert "Red Hat Ecosystem Catalog" in fc_dim["criteria"][0]["criterion"]

        # completeness should have 1 criterion
        comp_dim = next(d for d in dims if d["name"] == "completeness")
        assert comp_dim["criteria"] is not None
        assert len(comp_dim["criteria"]) == 1
        assert comp_dim["criteria"][0]["name"] == "covers_certification"

    def test_rubric_kit_format_variable_substitution(self):
        yaml_content = textwrap.dedent("""\
            variables:
              product: "Red Hat Enterprise Linux"
              version: "9.4"
            dimensions:
              - accuracy: "Accuracy of the answer"
                grading_type: score
                scores:
                  1: "Bad"
                  5: "Good"
            criteria:
              - name: mentions_product
                weight: 2
                dimension: accuracy
                criterion: "The answer must mention {{product}} version {{version}}."
        """)
        result = parse_rubric_yaml(yaml_content)
        dims = result["dimensions"]
        acc_dim = next(d for d in dims if d["name"] == "accuracy")
        assert acc_dim["criteria"] is not None
        crit_text = acc_dim["criteria"][0]["criterion"]
        assert "Red Hat Enterprise Linux" in crit_text
        assert "9.4" in crit_text
        assert "{{product}}" not in crit_text

    def test_rubric_kit_format_unresolved_variables_warns(self):
        yaml_content = textwrap.dedent("""\
            variables:
              product: "RHEL"
            dimensions:
              - accuracy: "Accuracy"
                grading_type: score
                scores:
                  1: "Bad"
                  5: "Good"
            criteria:
              - name: c1
                weight: 1
                dimension: accuracy
                criterion: "Must mention {{product}} and {{missing_var}}."
        """)
        with patch("app.services.rubric_service.logger") as mock_logger:
            result = parse_rubric_yaml(yaml_content)

        dims = result["dimensions"]
        acc_dim = next(d for d in dims if d["name"] == "accuracy")
        crit_text = acc_dim["criteria"][0]["criterion"]
        # product should be substituted, missing_var left as-is
        assert "RHEL" in crit_text
        assert "{{missing_var}}" in crit_text
        # Warning should have been logged via structlog
        mock_logger.warning.assert_called()
        call_args = mock_logger.warning.call_args
        assert call_args[0][0] == "rubric.variable_substitution.unresolved"
        assert "missing_var" in call_args[1]["unresolved_placeholders"]

    def test_rubric_kit_criteria_unknown_dimension_skipped(self):
        yaml_content = textwrap.dedent("""\
            dimensions:
              - accuracy: "Accuracy"
                grading_type: score
                scores:
                  1: "Bad"
                  5: "Good"
            criteria:
              - name: c1
                weight: 1
                dimension: accuracy
                criterion: "Valid criterion."
              - name: c2
                weight: 1
                dimension: nonexistent_dimension
                criterion: "This references a missing dimension."
        """)
        with patch("app.services.rubric_service.logger") as mock_logger:
            result = parse_rubric_yaml(yaml_content)

        dims = result["dimensions"]
        acc_dim = next(d for d in dims if d["name"] == "accuracy")
        # Should have only the valid criterion
        assert len(acc_dim["criteria"]) == 1
        assert acc_dim["criteria"][0]["name"] == "c1"
        # Warning about skipped criterion logged via structlog
        mock_logger.warning.assert_called()
        call_args = mock_logger.warning.call_args
        assert call_args[0][0] == "rubric.criteria.unknown_dimension"
        assert call_args[1]["dimension"] == "nonexistent_dimension"

    def test_simple_format_no_criteria(self):
        yaml_content = textwrap.dedent("""\
            dimensions:
              - name: quality
                weight: 1.0
                description: "Overall quality"
        """)
        result = parse_rubric_yaml(yaml_content)
        # Simple format dimensions should NOT have criteria
        assert "criteria" not in result["dimensions"][0]

    def test_empty_criteria_list_treated_as_none(self):
        yaml_content = textwrap.dedent("""\
            dimensions:
              - accuracy: "Accuracy"
                grading_type: score
                scores:
                  1: "Bad"
                  5: "Good"
            criteria: []
        """)
        result = parse_rubric_yaml(yaml_content)
        dims = result["dimensions"]
        # With empty criteria list, no criteria should be attached
        assert dims[0].get("criteria") is None


class TestConvertRubricKitPreservesCriteria:
    """Tests for convert_rubric_kit_to_internal preserving criteria."""

    def test_convert_rubric_kit_preserves_criteria(self):
        from rubric_kit import Criterion, Dimension, Rubric

        rubric = Rubric(
            dimensions=[
                Dimension(
                    name="accuracy",
                    description="Factual accuracy",
                    grading_type="score",
                    scores={1: "Bad", 5: "Good"},
                ),
                Dimension(
                    name="clarity",
                    description="Clarity",
                    grading_type="score",
                    scores={1: "Bad", 5: "Good"},
                ),
            ],
            criteria=[
                Criterion(name="fact_check", weight=3, dimension="accuracy", criterion="Is it factually correct?"),
                Criterion(name="sources", weight=2, dimension="accuracy", criterion="Does it cite sources?"),
                Criterion(name="readable", weight=1, dimension="clarity", criterion="Is it easy to read?"),
            ],
        )
        result = convert_rubric_kit_to_internal(rubric)
        acc_dim = next(d for d in result["dimensions"] if d["name"] == "accuracy")
        assert acc_dim["criteria"] is not None
        assert len(acc_dim["criteria"]) == 2
        assert acc_dim["criteria"][0]["name"] == "fact_check"
        assert acc_dim["criteria"][0]["weight"] == 3
        assert acc_dim["criteria"][1]["name"] == "sources"

        clar_dim = next(d for d in result["dimensions"] if d["name"] == "clarity")
        assert clar_dim["criteria"] is not None
        assert len(clar_dim["criteria"]) == 1
        assert clar_dim["criteria"][0]["name"] == "readable"


class TestSubstituteVariables:
    """Tests for _substitute_variables helper."""

    def test_replaces_single_variable(self):
        result = _substitute_variables("Hello {{name}}", {"name": "World"})
        assert result == "Hello World"

    def test_replaces_multiple_variables(self):
        result = _substitute_variables(
            "{{product}} version {{version}}",
            {"product": "RHEL", "version": "9.4"},
        )
        assert result == "RHEL version 9.4"

    def test_replaces_repeated_placeholder(self):
        result = _substitute_variables(
            "{{x}} and {{x}} again",
            {"x": "val"},
        )
        assert result == "val and val again"

    def test_empty_variables_returns_text_unchanged(self):
        assert _substitute_variables("{{keep}}", {}) == "{{keep}}"

    def test_no_placeholders_returns_text_unchanged(self):
        assert _substitute_variables("plain text", {"unused": "v"}) == "plain text"

    def test_non_string_variable_values_converted(self):
        result = _substitute_variables("count={{n}}", {"n": 42})
        assert result == "count=42"

    def test_empty_text_returns_empty(self):
        assert _substitute_variables("", {"key": "val"}) == ""

    def test_unresolved_placeholders_logged(self):
        with patch("app.services.rubric_service.logger") as mock_logger:
            result = _substitute_variables("{{known}} {{unknown}}", {"known": "ok"})
        assert result == "ok {{unknown}}"
        mock_logger.warning.assert_called_once()
        assert "unknown" in mock_logger.warning.call_args[1]["unresolved_placeholders"]


class TestRubricCriterionValidation:
    """Pydantic validation edge cases for RubricCriterion."""

    def test_empty_name_rejected(self):
        with pytest.raises(ValidationError):
            RubricCriterion(name="", criterion="text")

    def test_empty_criterion_text_allowed(self):
        c = RubricCriterion(name="c", criterion="")
        assert c.criterion == ""

    def test_zero_weight_rejected(self):
        with pytest.raises(ValidationError):
            RubricCriterion(name="c", criterion="text", weight=0)

    def test_negative_weight_rejected(self):
        with pytest.raises(ValidationError):
            RubricCriterion(name="c", criterion="text", weight=-1.0)

    def test_very_long_name_rejected(self):
        with pytest.raises(ValidationError):
            RubricCriterion(name="x" * 256, criterion="text")

    def test_max_length_name_accepted(self):
        c = RubricCriterion(name="x" * 255, criterion="text")
        assert len(c.name) == 255


class TestRubricKitCriteriaEdgeCases:
    """Edge-case tests for rubric-kit criteria import paths."""

    def test_criteria_as_dict_of_dicts(self):
        """Criteria provided as a mapping keyed by criterion name."""
        yaml_content = textwrap.dedent("""\
            dimensions:
              - accuracy: "Accuracy"
                grading_type: score
                scores:
                  1: "Bad"
                  5: "Good"
            criteria:
              fact_check:
                name: fact_check
                weight: 2
                dimension: accuracy
                criterion: "Is it factually correct?"
              source_check:
                name: source_check
                weight: 1
                dimension: accuracy
                criterion: "Does it cite sources?"
        """)
        result = parse_rubric_yaml(yaml_content)
        dims = result["dimensions"]
        acc_dim = next(d for d in dims if d["name"] == "accuracy")
        assert acc_dim["criteria"] is not None
        assert len(acc_dim["criteria"]) == 2

    def test_criteria_with_string_weight_defaults_to_one(self):
        """Non-numeric weight strings should fall back to 1."""
        yaml_content = textwrap.dedent("""\
            dimensions:
              - accuracy: "Accuracy"
                grading_type: score
                scores:
                  1: "Bad"
                  5: "Good"
            criteria:
              - name: c1
                weight: "high"
                dimension: accuracy
                criterion: "Some criterion."
        """)
        result = parse_rubric_yaml(yaml_content)
        dims = result["dimensions"]
        acc_dim = next(d for d in dims if d["name"] == "accuracy")
        assert acc_dim["criteria"][0]["weight"] == 1

    def test_criterion_missing_name_defaults_to_unnamed(self):
        """Criterion without a name field should get 'unnamed'."""
        yaml_content = textwrap.dedent("""\
            dimensions:
              - accuracy: "Accuracy"
                grading_type: score
                scores:
                  1: "Bad"
                  5: "Good"
            criteria:
              - weight: 1
                dimension: accuracy
                criterion: "Unnamed criterion text."
        """)
        result = parse_rubric_yaml(yaml_content)
        dims = result["dimensions"]
        acc_dim = next(d for d in dims if d["name"] == "accuracy")
        assert acc_dim["criteria"][0]["name"] == "unnamed"

    def test_criterion_missing_criterion_text_defaults_to_empty(self):
        """Criterion without criterion text should default to empty string."""
        yaml_content = textwrap.dedent("""\
            dimensions:
              - accuracy: "Accuracy"
                grading_type: score
                scores:
                  1: "Bad"
                  5: "Good"
            criteria:
              - name: c1
                weight: 1
                dimension: accuracy
        """)
        result = parse_rubric_yaml(yaml_content)
        dims = result["dimensions"]
        acc_dim = next(d for d in dims if d["name"] == "accuracy")
        assert acc_dim["criteria"][0]["criterion"] == ""

    def test_dimension_without_criteria_has_no_criteria_key(self):
        """Dimensions that have no matching criteria should omit the key."""
        yaml_content = textwrap.dedent("""\
            dimensions:
              - accuracy: "Accuracy"
                grading_type: score
                scores:
                  1: "Bad"
                  5: "Good"
              - clarity: "Clarity"
                grading_type: score
                scores:
                  1: "Bad"
                  5: "Good"
            criteria:
              - name: c1
                weight: 1
                dimension: accuracy
                criterion: "Only for accuracy."
        """)
        result = parse_rubric_yaml(yaml_content)
        dims = result["dimensions"]
        acc_dim = next(d for d in dims if d["name"] == "accuracy")
        clar_dim = next(d for d in dims if d["name"] == "clarity")
        assert "criteria" in acc_dim
        assert "criteria" not in clar_dim

    def test_multiple_criteria_same_dimension(self):
        """Multiple criteria mapping to a single dimension are all preserved."""
        yaml_content = textwrap.dedent("""\
            dimensions:
              - accuracy: "Accuracy"
                grading_type: score
                scores:
                  1: "Bad"
                  5: "Good"
            criteria:
              - name: c1
                weight: 1
                dimension: accuracy
                criterion: "First criterion."
              - name: c2
                weight: 2
                dimension: accuracy
                criterion: "Second criterion."
              - name: c3
                weight: 3
                dimension: accuracy
                criterion: "Third criterion."
        """)
        result = parse_rubric_yaml(yaml_content)
        dims = result["dimensions"]
        acc_dim = next(d for d in dims if d["name"] == "accuracy")
        assert len(acc_dim["criteria"]) == 3
        names = [c["name"] for c in acc_dim["criteria"]]
        assert names == ["c1", "c2", "c3"]

    def test_variables_none_treated_as_empty(self):
        """variables: null in YAML should not break criteria import."""
        yaml_content = textwrap.dedent("""\
            variables: null
            dimensions:
              - accuracy: "Accuracy"
                grading_type: score
                scores:
                  1: "Bad"
                  5: "Good"
            criteria:
              - name: c1
                weight: 1
                dimension: accuracy
                criterion: "Criterion with {{placeholder}}."
        """)
        result = parse_rubric_yaml(yaml_content)
        dims = result["dimensions"]
        acc_dim = next(d for d in dims if d["name"] == "accuracy")
        # placeholder should remain unresolved since variables is null
        assert "{{placeholder}}" in acc_dim["criteria"][0]["criterion"]

    def test_all_criteria_reference_unknown_dimensions(self):
        """When all criteria reference unknown dimensions, dimensions get no criteria."""
        yaml_content = textwrap.dedent("""\
            dimensions:
              - accuracy: "Accuracy"
                grading_type: score
                scores:
                  1: "Bad"
                  5: "Good"
            criteria:
              - name: c1
                weight: 1
                dimension: nonexistent
                criterion: "This goes nowhere."
        """)
        with patch("app.services.rubric_service.logger"):
            result = parse_rubric_yaml(yaml_content)
        dims = result["dimensions"]
        acc_dim = next(d for d in dims if d["name"] == "accuracy")
        assert "criteria" not in acc_dim


class TestConvertRubricKitEdgeCases:
    """Edge-case tests for convert_rubric_kit_to_internal."""

    def test_dimension_with_no_criteria_omits_key(self):
        from rubric_kit import Criterion, Dimension, Rubric

        rubric = Rubric(
            dimensions=[
                Dimension(name="d1", description="dim1", grading_type="score", scores={1: "Bad", 5: "Good"}),
                Dimension(name="d2", description="dim2", grading_type="score", scores={1: "Bad", 5: "Good"}),
            ],
            criteria=[
                Criterion(name="c1", weight=2, dimension="d1", criterion="Only for d1"),
            ],
        )
        result = convert_rubric_kit_to_internal(rubric)
        d1 = next(d for d in result["dimensions"] if d["name"] == "d1")
        d2 = next(d for d in result["dimensions"] if d["name"] == "d2")
        assert "criteria" in d1
        assert len(d1["criteria"]) == 1
        assert "criteria" not in d2

    def test_criterion_with_from_scores_weight_resolves_to_max_score(self):
        """rubric-kit Criterion with weight='from_scores' resolves to max score value."""
        from rubric_kit import Criterion, Dimension, Rubric

        rubric = Rubric(
            dimensions=[
                Dimension(name="d1", description="dim1", grading_type="score", scores={1: "Bad", 5: "Good"}),
            ],
            criteria=[
                Criterion(name="c1", weight="from_scores", dimension="d1", criterion="text"),
            ],
        )
        result = convert_rubric_kit_to_internal(rubric)
        d1 = next(d for d in result["dimensions"] if d["name"] == "d1")
        assert d1["criteria"][0]["weight"] == 5.0

    def test_custom_name_used(self):
        from rubric_kit import Criterion, Dimension, Rubric

        rubric = Rubric(
            dimensions=[
                Dimension(name="d1", description="dim1", grading_type="score", scores={1: "Bad", 5: "Good"}),
            ],
            criteria=[
                Criterion(name="c1", weight=1, dimension="d1", criterion="text"),
            ],
        )
        result = convert_rubric_kit_to_internal(rubric, name="Custom Name")
        assert result["name"] == "Custom Name"
