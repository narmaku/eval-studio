"""Unit tests for rubric service (import, generate, refine)."""

import os
import textwrap
from unittest.mock import patch

import pytest
from pydantic import ValidationError

from app.schemas.rubric import RubricCriterion, RubricDimension
from app.services.rubric_service import (
    _api_key_env_patch,
    _build_dimension_previews,
    _extract_system_config_metrics,
    _normalize_simple_dimensions,
    _parse_ls_eval_metric_format,
    _parse_system_config,
    _to_rubric_kit_format,
    analyze_rubric_yaml,
    clean_yaml_block,
    convert_rubric_kit_to_internal,
    detect_rubric_format,
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
        with pytest.raises(ValueError, match="Unrecognized rubric format"):
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

    def test_rubric_kit_format_unresolved_variables_raises(self):
        """Undefined variables now raise ValueError via rubric-kit validation."""
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
        with pytest.raises(ValueError, match="missing_var"):
            parse_rubric_yaml(yaml_content)

    def test_rubric_kit_criteria_unknown_dimension_raises(self):
        """Criteria referencing unknown dimensions now raise ValueError."""
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
        with pytest.raises(ValueError, match="nonexistent_dimension"):
            parse_rubric_yaml(yaml_content)

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

    def test_criteria_with_invalid_string_weight_raises(self):
        """Non-numeric weight strings are rejected by rubric-kit validation."""
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
        with pytest.raises(ValueError, match=r"[Ww]eight"):
            parse_rubric_yaml(yaml_content)

    def test_criterion_missing_name_gets_generated_name(self):
        """Criterion without a name field gets an auto-generated name."""
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
        # Auto-generated name from index
        assert acc_dim["criteria"][0]["name"] == "criterion_0"

    def test_criterion_missing_criterion_text_resolves_from_scores(self):
        """Criterion without criterion text resolves to score descriptions."""
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
        assert "1: Bad" in acc_dim["criteria"][0]["criterion"]
        assert "5: Good" in acc_dim["criteria"][0]["criterion"]

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

    def test_variables_none_with_placeholders_raises(self):
        """variables: null with unresolved placeholders raises ValueError."""
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
        with pytest.raises(ValueError, match="placeholder"):
            parse_rubric_yaml(yaml_content)

    def test_all_criteria_reference_unknown_dimensions_raises(self):
        """When all criteria reference unknown dimensions, ValueError is raised."""
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
        with pytest.raises(ValueError, match="nonexistent"):
            parse_rubric_yaml(yaml_content)


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


class TestRubricKitLoadRubricIntegration:
    """Tests for the load_rubric()-based rubric-kit import path."""

    def test_broken_dimension_raises_value_error(self):
        """Malformed dimension (score type without scores) raises ValueError."""
        yaml_content = textwrap.dedent("""\
            dimensions:
              - broken_dim: "Missing scores for score type"
                grading_type: score
            criteria:
              - name: c1
                weight: 1
                dimension: broken_dim
                criterion: "Some criterion."
        """)
        with pytest.raises(ValueError, match="scores"):
            parse_rubric_yaml(yaml_content)

    def test_from_scores_weight_resolves_to_max_score(self):
        """Criterion with weight: from_scores resolves to max score value."""
        yaml_content = textwrap.dedent("""\
            dimensions:
              - accuracy: "Accuracy"
                grading_type: score
                scores:
                  1: "Bad"
                  5: "Good"
            criteria:
              - name: c1
                weight: from_scores
                dimension: accuracy
                criterion: "Is it accurate?"
        """)
        result = parse_rubric_yaml(yaml_content)
        dims = result["dimensions"]
        acc_dim = next(d for d in dims if d["name"] == "accuracy")
        assert acc_dim["criteria"] is not None
        assert len(acc_dim["criteria"]) == 1
        assert acc_dim["criteria"][0]["weight"] == 5.0

    def test_from_scores_criterion_text_resolved(self):
        """Criterion with criterion: from_scores resolves to score descriptions."""
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
                criterion: "from_scores"
        """)
        result = parse_rubric_yaml(yaml_content)
        dims = result["dimensions"]
        acc_dim = next(d for d in dims if d["name"] == "accuracy")
        assert "1: Bad" in acc_dim["criteria"][0]["criterion"]
        assert "5: Good" in acc_dim["criteria"][0]["criterion"]

    def test_variables_none_without_placeholders_works(self):
        """variables: null without placeholders in criteria works fine."""
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
                criterion: "No placeholders here."
        """)
        result = parse_rubric_yaml(yaml_content)
        dims = result["dimensions"]
        acc_dim = next(d for d in dims if d["name"] == "accuracy")
        assert acc_dim["criteria"][0]["criterion"] == "No placeholders here."

    def test_rubric_kit_format_with_explicit_name_description_dims(self):
        """Dimensions with explicit name/description fields are parsed correctly."""
        yaml_content = textwrap.dedent("""\
            dimensions:
              - name: correctness
                description: "Factual accuracy"
                grading_type: score
                scores:
                  1: "Incorrect"
                  5: "Fully correct"
            criteria:
              - name: fact_check
                weight: 2
                dimension: correctness
                criterion: "Is the answer factually correct?"
        """)
        result = parse_rubric_yaml(yaml_content)
        assert len(result["dimensions"]) == 1
        assert result["dimensions"][0]["name"] == "correctness"
        assert result["dimensions"][0]["description"] == "Factual accuracy"
        assert result["dimensions"][0]["criteria"][0]["name"] == "fact_check"

    def test_rubric_kit_format_metadata_preserved(self):
        """Custom pass_threshold, aggregation, and prompt_template propagate in rubric-kit format."""
        yaml_content = textwrap.dedent("""\
            name: "Custom Meta Rubric"
            description: "Rubric with custom metadata"
            pass_threshold: 0.9
            aggregation: simple_average
            prompt_template: "Rate the response: {response}"
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
                criterion: "Is it accurate?"
        """)
        result = parse_rubric_yaml(yaml_content)
        assert result["name"] == "Custom Meta Rubric"
        assert result["description"] == "Rubric with custom metadata"
        assert result["pass_threshold"] == 0.9
        assert result["aggregation"] == "simple_average"
        assert result["prompt_template"] == "Rate the response: {response}"

    def test_rubric_kit_format_nested_rubric_key(self):
        """rubric-kit format YAML nested under 'rubric:' key is parsed correctly."""
        yaml_content = textwrap.dedent("""\
            rubric:
              name: "Nested Kit Rubric"
              description: "Nested rubric-kit format"
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
                  criterion: "Is it accurate?"
              pass_threshold: 0.85
        """)
        result = parse_rubric_yaml(yaml_content)
        assert result["name"] == "Nested Kit Rubric"
        assert result["description"] == "Nested rubric-kit format"
        assert result["pass_threshold"] == 0.85
        dims = result["dimensions"]
        assert len(dims) == 1
        assert dims[0]["name"] == "accuracy"
        assert dims[0]["criteria"][0]["name"] == "c1"

    def test_rubric_kit_format_validation_error_surfaces_as_value_error(self):
        """rubric-kit RubricValidationError is surfaced as ValueError."""
        yaml_content = textwrap.dedent("""\
            dimensions:
              - accuracy: "Accuracy"
                grading_type: score
            criteria:
              - name: c1
                weight: 1
                dimension: accuracy
                criterion: "Text."
        """)
        # grading_type: score without scores dict triggers RubricValidationError
        with pytest.raises(ValueError):
            parse_rubric_yaml(yaml_content)


class TestDetectRubricFormat:
    """Tests for detect_rubric_format heuristics."""

    def test_detect_ls_eval_system_config(self):
        data = {
            "metrics_metadata": {
                "turn_level": {
                    "geval:cla_tests_metric": {
                        "criteria": "Evaluate...",
                        "evaluation_steps": ["Step 1"],
                        "threshold": 0.9,
                    }
                }
            }
        }
        assert detect_rubric_format(data) == "ls_eval_system_config"

    def test_detect_ls_eval_system_config_conversation_level(self):
        data = {
            "metrics_metadata": {
                "conversation_level": {
                    "geval:coherence": {
                        "criteria": "Evaluate coherence...",
                    }
                }
            }
        }
        assert detect_rubric_format(data) == "ls_eval_system_config"

    def test_detect_ls_eval_metric_with_steps(self):
        data = {
            "criteria": "Evaluate correctness of the answer.",
            "evaluation_steps": ["Check factual accuracy", "Compare with reference"],
            "threshold": 0.9,
        }
        assert detect_rubric_format(data) == "ls_eval_metric"

    def test_detect_ls_eval_metric_with_params(self):
        data = {
            "criteria": "Evaluate the answer.",
            "evaluation_params": {"model": "gpt-4"},
        }
        assert detect_rubric_format(data) == "ls_eval_metric"

    def test_detect_ls_eval_metric_criteria_only(self):
        """Standalone ls-eval metric with criteria string but no dimensions."""
        data = {
            "criteria": "Evaluate the response quality.",
        }
        assert detect_rubric_format(data) == "ls_eval_metric"

    def test_ls_eval_metric_not_detected_when_dimensions_present(self):
        """When dimensions key is present, ls_eval_metric is not detected even if criteria string exists."""
        data = {
            "criteria": "Evaluate...",
            "dimensions": [{"name": "d1", "description": "dim1"}],
        }
        # criteria is a string but dimensions exist: NOT ls_eval_metric, falls to simple
        assert detect_rubric_format(data) == "simple"

    def test_detect_rubric_kit_format(self):
        data = {
            "dimensions": [
                {
                    "accuracy": "Factual accuracy",
                    "grading_type": "score",
                    "scores": {1: "Bad", 5: "Good"},
                }
            ],
            "criteria": [{"name": "c1", "weight": 1, "dimension": "accuracy", "criterion": "text"}],
        }
        assert detect_rubric_format(data) == "rubric_kit"

    def test_detect_simple_format(self):
        data = {"dimensions": [{"name": "quality", "weight": 1.0, "description": "Overall quality"}]}
        assert detect_rubric_format(data) == "simple"

    def test_detect_unknown_format(self):
        data = {"name": "something", "other_key": "value"}
        assert detect_rubric_format(data) == "unknown"

    def test_detect_empty_dict(self):
        assert detect_rubric_format({}) == "unknown"

    def test_ls_eval_metric_criteria_must_be_string(self):
        """If criteria is a list (rubric-kit style), it's not detected as ls_eval_metric."""
        data = {
            "criteria": [{"name": "c1", "criterion": "text"}],
            "evaluation_steps": ["Step 1"],
        }
        assert detect_rubric_format(data) != "ls_eval_metric"


class TestParseGevalFormat:
    """Tests for _parse_ls_eval_metric_format conversion."""

    def test_metric_with_evaluation_steps(self):
        data = {
            "criteria": "Evaluate correctness of the response.",
            "evaluation_steps": [
                "Check factual accuracy",
                "Compare with reference answer",
            ],
            "threshold": 0.9,
            "description": "Answer correctness metric",
        }
        result = _parse_ls_eval_metric_format(data)
        assert result["name"] == "Answer correctness metric"
        assert result["description"] == "Answer correctness metric"
        assert result["pass_threshold"] == 0.9
        assert len(result["dimensions"]) == 1

        dim = result["dimensions"][0]
        assert dim["name"] == "evaluation"
        assert dim["weight"] == 1.0
        assert dim["description"] == "Evaluate correctness of the response."
        assert len(dim["criteria"]) == 2
        assert dim["criteria"][0]["name"] == "step_1"
        assert dim["criteria"][0]["criterion"] == "Check factual accuracy"
        assert dim["criteria"][0]["weight"] == 1.0
        assert dim["criteria"][1]["name"] == "step_2"
        assert dim["criteria"][1]["criterion"] == "Compare with reference answer"

    def test_metric_criteria_only_no_steps(self):
        """When no evaluation_steps, creates a single criterion from criteria text."""
        data = {
            "criteria": "Evaluate the quality of the response.",
        }
        result = _parse_ls_eval_metric_format(data)
        assert len(result["dimensions"]) == 1
        dim = result["dimensions"][0]
        assert len(dim["criteria"]) == 1
        assert dim["criteria"][0]["name"] == "step_1"
        assert dim["criteria"][0]["criterion"] == "Evaluate the quality of the response."

    def test_metric_with_custom_name(self):
        data = {
            "criteria": "Evaluate...",
            "description": "Original name",
        }
        result = _parse_ls_eval_metric_format(data, name="Custom Name")
        assert result["name"] == "Custom Name"

    def test_metric_defaults(self):
        data = {"criteria": "Evaluate..."}
        result = _parse_ls_eval_metric_format(data)
        assert result["name"] == "Imported Rubric"
        assert result["pass_threshold"] == 0.7
        assert result["aggregation"] == "weighted_average"
        assert result["prompt_template"] is None

    def test_metric_name_from_description(self):
        data = {"criteria": "Evaluate...", "description": "My Metric"}
        result = _parse_ls_eval_metric_format(data)
        assert result["name"] == "My Metric"
        assert result["description"] == "My Metric"


class TestExtractSystemConfigMetrics:
    """Tests for _extract_system_config_metrics."""

    def test_extract_turn_level_metrics(self):
        data = {
            "metrics_metadata": {
                "turn_level": {
                    "geval:cla_tests_metric": {
                        "criteria": "Evaluate CLA tests...",
                        "evaluation_steps": ["Step 1"],
                        "threshold": 0.9,
                    },
                    "geval:technical_accuracy": {
                        "criteria": "Evaluate technical...",
                        "threshold": 0.7,
                    },
                }
            }
        }
        metrics = _extract_system_config_metrics(data)
        assert len(metrics) == 2
        ids = {m["metric_id"] for m in metrics}
        assert "geval:cla_tests_metric" in ids
        assert "geval:technical_accuracy" in ids
        assert all(m["level"] == "turn_level" for m in metrics)

    def test_extract_conversation_level_metrics(self):
        data = {
            "metrics_metadata": {
                "conversation_level": {
                    "geval:coherence": {
                        "criteria": "Evaluate conversation coherence...",
                    }
                }
            }
        }
        metrics = _extract_system_config_metrics(data)
        assert len(metrics) == 1
        assert metrics[0]["metric_id"] == "geval:coherence"
        assert metrics[0]["level"] == "conversation_level"

    def test_extract_both_levels(self):
        data = {
            "metrics_metadata": {
                "turn_level": {
                    "geval:accuracy": {"criteria": "Evaluate accuracy..."},
                },
                "conversation_level": {
                    "geval:coherence": {"criteria": "Evaluate coherence..."},
                },
            }
        }
        metrics = _extract_system_config_metrics(data)
        assert len(metrics) == 2

    def test_skips_non_ls_eval_metrics(self):
        data = {
            "metrics_metadata": {
                "turn_level": {
                    "geval:accuracy": {"criteria": "Evaluate..."},
                    "bleu_score": {"some_param": "value"},
                }
            }
        }
        metrics = _extract_system_config_metrics(data)
        assert len(metrics) == 1
        assert metrics[0]["metric_id"] == "geval:accuracy"

    def test_empty_metrics_metadata(self):
        data = {"metrics_metadata": {}}
        metrics = _extract_system_config_metrics(data)
        assert metrics == []


class TestParseSystemConfig:
    """Tests for _parse_system_config."""

    def test_parse_specific_metric(self):
        data = {
            "metrics_metadata": {
                "turn_level": {
                    "geval:accuracy": {
                        "criteria": "Evaluate factual accuracy.",
                        "evaluation_steps": ["Check facts", "Verify sources"],
                        "threshold": 0.9,
                        "description": "Accuracy metric",
                    },
                    "geval:coherence": {
                        "criteria": "Evaluate coherence...",
                    },
                }
            }
        }
        result = _parse_system_config(data, metric_id="geval:accuracy")
        assert result["name"] == "Accuracy metric"
        assert result["pass_threshold"] == 0.9
        assert len(result["dimensions"]) == 1
        assert len(result["dimensions"][0]["criteria"]) == 2

    def test_parse_first_metric_when_none_specified(self):
        data = {
            "metrics_metadata": {
                "turn_level": {
                    "geval:accuracy": {
                        "criteria": "Evaluate...",
                        "description": "First metric",
                    },
                }
            }
        }
        result = _parse_system_config(data)
        assert result["name"] == "First metric"

    def test_parse_unknown_metric_id_raises(self):
        data = {
            "metrics_metadata": {
                "turn_level": {
                    "geval:accuracy": {"criteria": "Evaluate..."},
                }
            }
        }
        with pytest.raises(ValueError, match="not found"):
            _parse_system_config(data, metric_id="geval:nonexistent")

    def test_parse_no_metrics_raises(self):
        data = {"metrics_metadata": {}}
        with pytest.raises(ValueError, match="No ls-eval metrics"):
            _parse_system_config(data)


class TestAnalyzeRubricYaml:
    """Tests for the analyze_rubric_yaml service function."""

    def test_analyze_simple_format(self):
        yaml_content = textwrap.dedent("""\
            name: "Simple Rubric"
            description: "A simple rubric"
            dimensions:
              - name: accuracy
                weight: 0.6
                description: "Factual accuracy"
              - name: completeness
                weight: 0.4
                description: "Completeness"
            pass_threshold: 0.8
        """)
        result = analyze_rubric_yaml(yaml_content)
        assert result["detected_format"] == "simple"
        assert len(result["metrics"]) == 1
        metric = result["metrics"][0]
        assert metric["suggested_name"] == "Simple Rubric"
        assert metric["suggested_description"] == "A simple rubric"
        assert len(metric["dimensions_preview"]) == 2
        assert metric["dimensions_preview"][0]["name"] == "accuracy"
        assert metric["pass_threshold"] == 0.8

    def test_analyze_rubric_kit_format(self):
        yaml_content = textwrap.dedent("""\
            name: "Kit Rubric"
            dimensions:
              - accuracy: "Factual accuracy"
                grading_type: score
                scores:
                  1: "Bad"
                  5: "Good"
            criteria:
              - name: c1
                weight: 2
                dimension: accuracy
                criterion: "Is it accurate?"
              - name: c2
                weight: 1
                dimension: accuracy
                criterion: "Does it cite sources?"
        """)
        result = analyze_rubric_yaml(yaml_content)
        assert result["detected_format"] == "rubric_kit"
        assert len(result["metrics"]) == 1
        metric = result["metrics"][0]
        assert metric["suggested_name"] == "Kit Rubric"
        assert len(metric["dimensions_preview"]) == 1
        assert metric["dimensions_preview"][0]["criteria_count"] == 2

    def test_analyze_ls_eval_metric_format(self):
        yaml_content = textwrap.dedent("""\
            criteria: "Evaluate the correctness of the response."
            evaluation_steps:
              - "Check factual accuracy"
              - "Compare with reference"
            threshold: 0.9
            description: "Correctness metric"
        """)
        result = analyze_rubric_yaml(yaml_content)
        assert result["detected_format"] == "ls_eval_metric"
        assert len(result["metrics"]) == 1
        metric = result["metrics"][0]
        assert metric["suggested_name"] == "Correctness metric"
        assert metric["pass_threshold"] == 0.9
        assert metric["criteria_count"] == 2

    def test_analyze_system_config(self):
        yaml_content = textwrap.dedent("""\
            metrics_metadata:
              turn_level:
                "geval:accuracy":
                  criteria: "Evaluate accuracy..."
                  evaluation_steps:
                    - "Step 1"
                    - "Step 2"
                  threshold: 0.9
                  description: "Accuracy metric"
                "geval:coherence":
                  criteria: "Evaluate coherence..."
                  description: "Coherence metric"
        """)
        result = analyze_rubric_yaml(yaml_content)
        assert result["detected_format"] == "ls_eval_system_config"
        assert len(result["metrics"]) == 2
        names = {m["suggested_name"] for m in result["metrics"]}
        assert "Accuracy metric" in names
        assert "Coherence metric" in names
        # Each metric should have a metric_id
        ids = {m["metric_id"] for m in result["metrics"]}
        assert "geval:accuracy" in ids
        assert "geval:coherence" in ids

    def test_analyze_invalid_yaml(self):
        with pytest.raises(ValueError, match="Invalid YAML"):
            analyze_rubric_yaml("::invalid yaml: [")

    def test_analyze_unknown_format(self):
        yaml_content = "name: just a name"
        result = analyze_rubric_yaml(yaml_content)
        assert result["detected_format"] == "unknown"
        assert result["metrics"] == []


class TestParseRubricYamlMultiFormat:
    """Tests for parse_rubric_yaml with ls-eval metric and system config formats."""

    def test_parse_ls_eval_metric_format(self):
        yaml_content = textwrap.dedent("""\
            criteria: "Evaluate the correctness of the response."
            evaluation_steps:
              - "Check factual accuracy"
              - "Compare with reference"
            threshold: 0.9
            description: "Correctness metric"
        """)
        result = parse_rubric_yaml(yaml_content)
        assert result["name"] == "Correctness metric"
        assert result["pass_threshold"] == 0.9
        assert len(result["dimensions"]) == 1
        assert result["dimensions"][0]["name"] == "evaluation"
        assert len(result["dimensions"][0]["criteria"]) == 2

    def test_parse_system_config_format(self):
        yaml_content = textwrap.dedent("""\
            metrics_metadata:
              turn_level:
                "geval:accuracy":
                  criteria: "Evaluate accuracy..."
                  evaluation_steps:
                    - "Check facts"
                  threshold: 0.8
                  description: "Accuracy"
        """)
        result = parse_rubric_yaml(yaml_content)
        assert result["name"] == "Accuracy"
        assert result["pass_threshold"] == 0.8

    def test_parse_system_config_with_metric_id(self):
        yaml_content = textwrap.dedent("""\
            metrics_metadata:
              turn_level:
                "geval:accuracy":
                  criteria: "Evaluate accuracy..."
                  description: "Accuracy"
                "geval:coherence":
                  criteria: "Evaluate coherence..."
                  description: "Coherence"
        """)
        result = parse_rubric_yaml(yaml_content, metric_id="geval:coherence")
        assert result["name"] == "Coherence"

    def test_parse_unknown_format_raises(self):
        yaml_content = "name: just a name"
        with pytest.raises(ValueError, match="Unrecognized rubric format"):
            parse_rubric_yaml(yaml_content)

    def test_existing_simple_format_still_works(self):
        """Backward compatibility: simple format with dimensions still parses."""
        yaml_content = textwrap.dedent("""\
            name: "Simple"
            dimensions:
              - name: quality
                weight: 1.0
                description: "Quality"
        """)
        result = parse_rubric_yaml(yaml_content)
        assert result["name"] == "Simple"
        assert len(result["dimensions"]) == 1

    def test_existing_rubric_kit_format_still_works(self):
        """Backward compatibility: rubric-kit format still parses."""
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
                criterion: "Accurate?"
        """)
        result = parse_rubric_yaml(yaml_content)
        assert len(result["dimensions"]) == 1
        assert result["dimensions"][0]["name"] == "accuracy"


class TestExtractSystemConfigMetricsEdgeCases:
    """Edge cases for _extract_system_config_metrics."""

    def test_non_dict_metrics_metadata_returns_empty(self):
        """When metrics_metadata is not a dict (e.g., a list), return empty list."""
        data = {"metrics_metadata": ["not", "a", "dict"]}
        assert _extract_system_config_metrics(data) == []

    def test_non_dict_metric_data_skipped(self):
        """When a metric value is not a dict, it is skipped."""
        data = {
            "metrics_metadata": {
                "turn_level": {
                    "geval:accuracy": "just a string, not a dict",
                    "geval:coherence": {"criteria": "Evaluate..."},
                }
            }
        }
        metrics = _extract_system_config_metrics(data)
        assert len(metrics) == 1
        assert metrics[0]["metric_id"] == "geval:coherence"

    def test_non_dict_level_value_skipped(self):
        """When a level value (turn_level/conversation_level) is not a dict, skip it."""
        data = {"metrics_metadata": {"turn_level": "not a dict"}}
        assert _extract_system_config_metrics(data) == []

    def test_missing_metrics_metadata_returns_empty(self):
        """When metrics_metadata key is absent, return empty list."""
        data = {"other_key": "value"}
        assert _extract_system_config_metrics(data) == []


class TestAnalyzeRubricYamlEdgeCases:
    """Edge cases for analyze_rubric_yaml."""

    def test_analyze_non_dict_yaml_returns_unknown(self):
        """YAML that parses to a scalar (not dict) returns unknown format."""
        result = analyze_rubric_yaml("just a plain string")
        assert result["detected_format"] == "unknown"
        assert result["metrics"] == []

    def test_analyze_null_yaml_returns_unknown(self):
        """YAML null returns unknown format."""
        result = analyze_rubric_yaml("null")
        assert result["detected_format"] == "unknown"
        assert result["metrics"] == []

    def test_analyze_list_yaml_returns_unknown(self):
        """YAML that parses to a list returns unknown format."""
        result = analyze_rubric_yaml("- item1\n- item2")
        assert result["detected_format"] == "unknown"
        assert result["metrics"] == []

    def test_analyze_rubric_kit_format_validation_failure_returns_empty_metrics(self):
        """When rubric-kit parsing fails, analyze returns format with empty metrics."""
        yaml_content = textwrap.dedent("""\
            dimensions:
              - broken: "Missing scores for score type"
                grading_type: score
            criteria:
              - name: c1
                weight: 1
                dimension: broken
                criterion: "Some criterion."
        """)
        result = analyze_rubric_yaml(yaml_content)
        assert result["detected_format"] == "rubric_kit"
        assert result["metrics"] == []

    def test_analyze_with_nested_rubric_key(self):
        """Analyze correctly unwraps nested 'rubric:' key."""
        yaml_content = textwrap.dedent("""\
            rubric:
              name: "Nested"
              dimensions:
                - name: quality
                  weight: 1.0
                  description: "Quality"
        """)
        result = analyze_rubric_yaml(yaml_content)
        assert result["detected_format"] == "simple"
        assert result["metrics"][0]["suggested_name"] == "Nested"


class TestNormalizeSimpleDimensionsEdgeCases:
    """Edge cases for _normalize_simple_dimensions."""

    def test_non_dict_entries_skipped(self):
        """Non-dict items in the dimensions list are skipped."""
        dims = _normalize_simple_dimensions(
            [
                {"name": "quality", "weight": 1.0, "description": "Quality"},
                "not a dict",
                42,
                None,
            ]
        )
        assert len(dims) == 1
        assert dims[0]["name"] == "quality"

    def test_empty_list_returns_empty(self):
        """Empty dimensions list returns empty."""
        assert _normalize_simple_dimensions([]) == []

    def test_missing_fields_use_defaults(self):
        """Dimensions without name/weight/description get defaults."""
        dims = _normalize_simple_dimensions([{}])
        assert len(dims) == 1
        assert dims[0]["name"] == "unnamed"
        assert dims[0]["weight"] == 1.0
        assert dims[0]["description"] == "unnamed"


class TestToRubricKitFormat:
    """Tests for _to_rubric_kit_format conversion."""

    def test_converts_dimensions_with_name_description(self):
        """Dimensions with explicit name/description are converted to key-based format."""
        data = {
            "dimensions": [
                {"name": "accuracy", "description": "Factual accuracy", "grading_type": "score", "scores": {1: "Bad"}}
            ],
        }
        result = _to_rubric_kit_format(data)
        dim = result["dimensions"][0]
        assert "accuracy" in dim
        assert dim["accuracy"] == "Factual accuracy"
        assert "name" not in dim
        assert "description" not in dim
        assert dim["grading_type"] == "score"

    def test_dimension_without_name_passed_through(self):
        """Dict dimensions without name field are passed through as-is."""
        data = {
            "dimensions": [{"accuracy": "Factual accuracy", "grading_type": "score"}],
        }
        result = _to_rubric_kit_format(data)
        assert result["dimensions"][0]["accuracy"] == "Factual accuracy"

    def test_non_dict_dimension_passed_through(self):
        """Non-dict entries in dimensions are appended as-is."""
        data = {"dimensions": ["a string entry", 42]}
        result = _to_rubric_kit_format(data)
        assert result["dimensions"] == ["a string entry", 42]

    def test_criteria_list_converted_to_dict(self):
        """Criteria as a list of dicts is converted to dict-of-dicts format."""
        data = {
            "criteria": [
                {"name": "c1", "weight": 1, "dimension": "d1", "criterion": "text1"},
                {"name": "c2", "weight": 2, "dimension": "d1", "criterion": "text2"},
            ]
        }
        result = _to_rubric_kit_format(data)
        assert "c1" in result["criteria"]
        assert "c2" in result["criteria"]
        assert "name" not in result["criteria"]["c1"]
        assert result["criteria"]["c1"]["weight"] == 1

    def test_criteria_without_name_gets_generated_name(self):
        """Criteria without a name field get auto-generated names."""
        data = {
            "criteria": [
                {"weight": 1, "dimension": "d1", "criterion": "text1"},
            ]
        }
        result = _to_rubric_kit_format(data)
        assert "criterion_0" in result["criteria"]

    def test_criteria_dict_passed_through(self):
        """Criteria already as a dict is passed through unchanged."""
        data = {"criteria": {"c1": {"weight": 1, "dimension": "d1", "criterion": "text"}}}
        result = _to_rubric_kit_format(data)
        assert result["criteria"] == data["criteria"]

    def test_variables_copied(self):
        """Variables key is copied to result."""
        data = {"variables": {"product": "RHEL"}}
        result = _to_rubric_kit_format(data)
        assert result["variables"] == {"product": "RHEL"}

    def test_no_variables_key_omitted(self):
        """When no variables key exists, it is not in result."""
        data = {"dimensions": []}
        result = _to_rubric_kit_format(data)
        assert "variables" not in result


class TestBuildDimensionPreviews:
    """Tests for _build_dimension_previews helper."""

    def test_builds_previews_from_dimensions(self):
        dimensions = [
            {"name": "accuracy", "description": "Factual accuracy", "weight": 0.6, "criteria": [{"name": "c1"}]},
            {"name": "clarity", "description": "Clear writing", "weight": 0.4, "criteria": []},
        ]
        previews = _build_dimension_previews(dimensions)
        assert len(previews) == 2
        assert previews[0]["name"] == "accuracy"
        assert previews[0]["criteria_count"] == 1
        assert previews[1]["name"] == "clarity"
        assert previews[1]["criteria_count"] == 0

    def test_missing_fields_use_defaults(self):
        """Dimensions missing optional fields get default values."""
        dimensions = [{}]
        previews = _build_dimension_previews(dimensions)
        assert previews[0]["name"] == "unnamed"
        assert previews[0]["description"] == ""
        assert previews[0]["weight"] == 1.0
        assert previews[0]["criteria_count"] == 0


class TestConvertRubricKitToInternalEdgeCases:
    """Tests for edge cases in convert_rubric_kit_to_internal."""

    def test_criterion_with_non_int_weight_defaults_to_one(self):
        """Non-int, non-from_scores weight falls back to 1.0 in convert_rubric_kit_to_internal."""
        from unittest.mock import MagicMock

        # rubric-kit Criterion validates weight strictly, so use a mock
        # to exercise the defensive else branch in convert_rubric_kit_to_internal
        from rubric_kit import Dimension, Rubric

        dim = Dimension(name="d1", description="dim1", grading_type="score", scores={1: "Bad", 5: "Good"})
        crit = MagicMock()
        crit.name = "c1"
        crit.weight = "some_string"
        crit.dimension = "d1"
        crit.criterion = "text"

        rubric = MagicMock(spec=Rubric)
        rubric.dimensions = [dim]
        rubric.criteria = [crit]

        result = convert_rubric_kit_to_internal(rubric)
        d = result["dimensions"][0]
        assert d["criteria"][0]["weight"] == 1.0

    def test_criterion_none_text_without_scores_defaults_to_empty(self):
        """When criterion text is None and dimension has no scores, defaults to empty string."""
        from rubric_kit import Criterion, Dimension, Rubric

        rubric = Rubric(
            dimensions=[
                Dimension(name="d1", description="dim1", grading_type="binary"),
            ],
            criteria=[
                Criterion(name="c1", weight=1, dimension="d1", criterion=None),
            ],
        )
        result = convert_rubric_kit_to_internal(rubric)
        dim = result["dimensions"][0]
        assert dim["criteria"][0]["criterion"] == ""

    def test_from_scores_weight_without_scores_defaults_to_one(self):
        """weight: from_scores on dimension with no scores falls back to 1.0."""
        from rubric_kit import Criterion, Dimension, Rubric

        rubric = Rubric(
            dimensions=[
                Dimension(name="d1", description="dim1", grading_type="binary"),
            ],
            criteria=[
                Criterion(name="c1", weight="from_scores", dimension="d1", criterion="text"),
            ],
        )
        result = convert_rubric_kit_to_internal(rubric)
        dim = result["dimensions"][0]
        assert dim["criteria"][0]["weight"] == 1.0

    def test_from_scores_text_without_scores_defaults_to_empty(self):
        """criterion: from_scores on dimension with no scores defaults to empty string."""
        from rubric_kit import Criterion, Dimension, Rubric

        rubric = Rubric(
            dimensions=[
                Dimension(name="d1", description="dim1", grading_type="binary"),
            ],
            criteria=[
                Criterion(name="c1", weight=1, dimension="d1", criterion="from_scores"),
            ],
        )
        result = convert_rubric_kit_to_internal(rubric)
        dim = result["dimensions"][0]
        assert dim["criteria"][0]["criterion"] == ""


class TestApiKeyEnvPatch:
    """Tests for _api_key_env_patch context manager."""

    def test_no_api_key_is_noop(self):
        """When api_key is None, env is not modified."""
        original = os.environ.get("LITELLM_API_KEY")
        with _api_key_env_patch(None):
            assert os.environ.get("LITELLM_API_KEY") == original

    def test_sets_and_clears_env_var(self):
        """When api_key is set and no prior value, env var is set then cleared."""
        os.environ.pop("LITELLM_API_KEY", None)
        with _api_key_env_patch("test-key-123"):
            assert os.environ["LITELLM_API_KEY"] == "test-key-123"
        assert "LITELLM_API_KEY" not in os.environ

    def test_restores_previous_env_var(self):
        """When there was a prior LITELLM_API_KEY, it is restored after context."""
        os.environ["LITELLM_API_KEY"] = "original-key"
        try:
            with _api_key_env_patch("temp-key"):
                assert os.environ["LITELLM_API_KEY"] == "temp-key"
            assert os.environ["LITELLM_API_KEY"] == "original-key"
        finally:
            os.environ.pop("LITELLM_API_KEY", None)

    def test_empty_string_api_key_is_noop(self):
        """Empty string api_key is falsy, so context is a no-op."""
        with _api_key_env_patch(""):
            pass  # Should not raise
