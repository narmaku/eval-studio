"""Unit tests for the evaluation adapter factory."""

import pytest

from app.adapters.factory import create_evaluation_adapter
from app.adapters.litellm_judge import LiteLLMJudgeAdapter


def test_create_litellm_adapter():
    """Factory creates LiteLLMJudgeAdapter via registry."""
    adapter = create_evaluation_adapter(
        adapter_type="litellm-judge",
        model="gpt-4",
        api_key="sk-test",
        api_base="http://localhost:8080/v1",
    )
    assert isinstance(adapter, LiteLLMJudgeAdapter)
    assert adapter.model == "gpt-4"
    assert adapter.api_key == "sk-test"
    assert adapter.api_base == "http://localhost:8080/v1"


def test_create_litellm_adapter_default_type():
    """Factory defaults to 'litellm-judge' when adapter_type is not specified."""
    adapter = create_evaluation_adapter(model="gpt-4")
    assert isinstance(adapter, LiteLLMJudgeAdapter)
    assert adapter.model == "gpt-4"


def test_create_litellm_adapter_with_concurrency():
    """Factory passes max_concurrency to LiteLLMJudgeAdapter."""
    adapter = create_evaluation_adapter(model="gpt-4", max_concurrency=5)
    assert isinstance(adapter, LiteLLMJudgeAdapter)
    assert adapter._semaphore._value == 5


def test_unknown_adapter_type():
    """Factory raises ValueError for unknown adapter_type."""
    with pytest.raises(ValueError, match="Unknown evaluation adapter type: custom_judge"):
        create_evaluation_adapter(adapter_type="custom_judge")
