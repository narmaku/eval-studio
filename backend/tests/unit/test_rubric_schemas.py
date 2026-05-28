"""Unit tests for Rubric Pydantic schemas."""

import pytest
from pydantic import ValidationError

from app.schemas.rubric import (
    RubricCreate,
    RubricDimension,
    RubricGenerateRequest,
    RubricImportRequest,
    RubricRefineRequest,
    RubricResponse,
    RubricUpdate,
)


class TestRubricDimension:
    def test_valid_dimension(self):
        dim = RubricDimension(name="accuracy", weight=1.0, description="How accurate is the answer")
        assert dim.name == "accuracy"
        assert dim.weight == 1.0
        assert dim.description == "How accurate is the answer"

    def test_negative_weight_rejected(self):
        with pytest.raises(ValidationError):
            RubricDimension(name="accuracy", weight=-0.5, description="bad weight")

    def test_zero_weight_rejected(self):
        with pytest.raises(ValidationError):
            RubricDimension(name="accuracy", weight=0.0, description="zero weight")

    def test_empty_name_rejected(self):
        with pytest.raises(ValidationError):
            RubricDimension(name="", weight=1.0, description="valid description")

    def test_name_too_long_rejected(self):
        with pytest.raises(ValidationError):
            RubricDimension(name="a" * 256, weight=1.0, description="valid description")

    def test_empty_description_rejected(self):
        with pytest.raises(ValidationError):
            RubricDimension(name="accuracy", weight=1.0, description="")


class TestRubricCreate:
    def test_valid_create(self):
        rubric = RubricCreate(
            name="Test Rubric",
            dimensions=[RubricDimension(name="accuracy", weight=1.0, description="Accuracy")],
        )
        assert rubric.name == "Test Rubric"
        assert len(rubric.dimensions) == 1
        assert rubric.pass_threshold == 0.7
        assert rubric.aggregation == "weighted_average"
        assert rubric.description is None
        assert rubric.prompt_template is None

    def test_empty_name_rejected(self):
        with pytest.raises(ValidationError):
            RubricCreate(
                name="",
                dimensions=[RubricDimension(name="accuracy", weight=1.0, description="Accuracy")],
            )

    def test_name_too_long_rejected(self):
        with pytest.raises(ValidationError):
            RubricCreate(
                name="a" * 256,
                dimensions=[RubricDimension(name="accuracy", weight=1.0, description="Accuracy")],
            )

    def test_empty_dimensions_rejected(self):
        with pytest.raises(ValidationError):
            RubricCreate(name="Test", dimensions=[])

    def test_pass_threshold_below_zero_rejected(self):
        with pytest.raises(ValidationError):
            RubricCreate(
                name="Test",
                dimensions=[RubricDimension(name="accuracy", weight=1.0, description="Accuracy")],
                pass_threshold=-0.1,
            )

    def test_pass_threshold_above_one_rejected(self):
        with pytest.raises(ValidationError):
            RubricCreate(
                name="Test",
                dimensions=[RubricDimension(name="accuracy", weight=1.0, description="Accuracy")],
                pass_threshold=1.1,
            )

    def test_all_fields(self):
        rubric = RubricCreate(
            name="Full Rubric",
            description="A full rubric",
            dimensions=[
                RubricDimension(name="accuracy", weight=0.6, description="Accuracy"),
                RubricDimension(name="completeness", weight=0.4, description="Completeness"),
            ],
            pass_threshold=0.8,
            aggregation="simple_average",
            prompt_template="Rate the following: {response}",
        )
        assert rubric.description == "A full rubric"
        assert len(rubric.dimensions) == 2
        assert rubric.pass_threshold == 0.8
        assert rubric.aggregation == "simple_average"
        assert rubric.prompt_template == "Rate the following: {response}"


class TestRubricUpdate:
    def test_all_fields_optional(self):
        update = RubricUpdate()
        assert update.name is None
        assert update.description is None
        assert update.dimensions is None
        assert update.pass_threshold is None
        assert update.aggregation is None
        assert update.prompt_template is None

    def test_partial_update(self):
        update = RubricUpdate(name="New Name", pass_threshold=0.9)
        assert update.name == "New Name"
        assert update.pass_threshold == 0.9
        assert update.dimensions is None

    def test_negative_weight_in_update_rejected(self):
        with pytest.raises(ValidationError):
            RubricUpdate(dimensions=[RubricDimension(name="accuracy", weight=-1.0, description="bad")])

    def test_empty_dimensions_in_update_rejected(self):
        with pytest.raises(ValidationError):
            RubricUpdate(dimensions=[])


class TestRubricResponse:
    def test_from_attributes(self):
        assert RubricResponse.model_config.get("from_attributes") is True


class TestRubricImportRequest:
    def test_valid_import(self):
        req = RubricImportRequest(yaml_content="name: test\ndimensions: []")
        assert req.yaml_content == "name: test\ndimensions: []"

    def test_empty_yaml_content_rejected(self):
        with pytest.raises(ValidationError):
            RubricImportRequest(yaml_content="")


class TestRubricGenerateRequest:
    def test_valid_generate(self):
        req = RubricGenerateRequest(description="Evaluate accuracy", provider_id="openai-gpt4")
        assert req.description == "Evaluate accuracy"
        assert req.provider_id == "openai-gpt4"
        assert req.sample_data is None

    def test_with_sample_data(self):
        req = RubricGenerateRequest(
            description="Evaluate accuracy", provider_id="openai-gpt4", sample_data="Q: What? A: This."
        )
        assert req.sample_data == "Q: What? A: This."

    def test_empty_description_rejected(self):
        with pytest.raises(ValidationError):
            RubricGenerateRequest(description="", provider_id="openai-gpt4")

    def test_empty_provider_id_rejected(self):
        with pytest.raises(ValidationError):
            RubricGenerateRequest(description="test", provider_id="")


class TestRubricRefineRequest:
    def test_valid_refine(self):
        req = RubricRefineRequest(feedback="Add completeness", provider_id="openai-gpt4")
        assert req.feedback == "Add completeness"
        assert req.provider_id == "openai-gpt4"

    def test_empty_feedback_rejected(self):
        with pytest.raises(ValidationError):
            RubricRefineRequest(feedback="", provider_id="openai-gpt4")

    def test_empty_provider_id_rejected(self):
        with pytest.raises(ValidationError):
            RubricRefineRequest(feedback="test", provider_id="")
