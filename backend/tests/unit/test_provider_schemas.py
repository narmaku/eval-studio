"""Unit tests for Provider Pydantic schemas."""

import pytest
from pydantic import ValidationError

from app.schemas.provider import ProviderCreate, ProviderResponse, ProviderUpdate


class TestProviderCreate:
    def test_valid_create(self):
        provider = ProviderCreate(name="My LLM", litellm_model="openai/gpt-4")
        assert provider.name == "My LLM"
        assert provider.litellm_model == "openai/gpt-4"
        assert provider.api_base is None
        assert provider.api_key_env is None
        assert provider.proxy is None
        assert provider.tags == []
        assert provider.purpose == "test"

    def test_all_fields(self):
        provider = ProviderCreate(
            name="Full Provider",
            litellm_model="anthropic/claude-3",
            api_base="https://api.example.com",
            api_key_env="MY_API_KEY",
            proxy="http://proxy:3128",
            tags=["fast", "judge"],
            purpose="judge",
        )
        assert provider.api_base == "https://api.example.com"
        assert provider.api_key_env == "MY_API_KEY"
        assert provider.proxy == "http://proxy:3128"
        assert provider.tags == ["fast", "judge"]
        assert provider.purpose == "judge"

    def test_empty_name_rejected(self):
        with pytest.raises(ValidationError):
            ProviderCreate(name="", litellm_model="openai/gpt-4")

    def test_name_too_long_rejected(self):
        with pytest.raises(ValidationError):
            ProviderCreate(name="a" * 256, litellm_model="openai/gpt-4")

    def test_empty_litellm_model_rejected(self):
        with pytest.raises(ValidationError):
            ProviderCreate(name="My LLM", litellm_model="")

    def test_litellm_model_too_long_rejected(self):
        with pytest.raises(ValidationError):
            ProviderCreate(name="My LLM", litellm_model="a" * 256)


class TestProviderUpdate:
    def test_all_fields_optional(self):
        update = ProviderUpdate()
        assert update.name is None
        assert update.litellm_model is None
        assert update.api_base is None
        assert update.api_key_env is None
        assert update.proxy is None
        assert update.tags is None
        assert update.purpose is None

    def test_partial_update(self):
        update = ProviderUpdate(name="New Name", purpose="judge")
        assert update.name == "New Name"
        assert update.purpose == "judge"
        assert update.litellm_model is None

    def test_empty_name_in_update_rejected(self):
        with pytest.raises(ValidationError):
            ProviderUpdate(name="")


class TestProviderResponse:
    def test_from_attributes(self):
        assert ProviderResponse.model_config.get("from_attributes") is True

    def test_defaults(self):
        resp = ProviderResponse(id="p-1", name="Test", litellm_model="m")
        assert resp.source == "yaml"
        assert resp.has_api_key is False
        assert resp.created_at is None
        assert resp.updated_at is None
        assert resp.tags == []
        assert resp.purpose == "test"
