"""Unit tests for Provider Pydantic schemas."""

import pytest
from pydantic import ValidationError

from app.schemas.provider import ProviderCreate, ProviderResponse, ProviderUpdate


class TestProviderCreate:
    def test_valid_create(self):
        provider = ProviderCreate(name="My LLM", default_model="openai/gpt-4")
        assert provider.name == "My LLM"
        assert provider.default_model == "openai/gpt-4"
        assert provider.api_base is None
        assert provider.api_key_env is None
        assert provider.proxy is None
        assert provider.tags == []

    def test_all_fields(self):
        provider = ProviderCreate(
            name="Full Provider",
            default_model="anthropic/claude-3",
            api_base="https://api.example.com",
            api_key_env="MY_API_KEY",
            proxy="http://proxy:3128",
            tags=["fast", "judge"],
        )
        assert provider.api_base == "https://api.example.com"
        assert provider.api_key_env == "MY_API_KEY"
        assert provider.proxy == "http://proxy:3128"
        assert provider.tags == ["fast", "judge"]

    def test_empty_name_rejected(self):
        with pytest.raises(ValidationError):
            ProviderCreate(name="", default_model="openai/gpt-4")

    def test_name_too_long_rejected(self):
        with pytest.raises(ValidationError):
            ProviderCreate(name="a" * 256, default_model="openai/gpt-4")

    def test_empty_litellm_model_allowed_for_custom(self):
        """Custom providers don't need a litellm_model."""
        provider = ProviderCreate(name="My Custom", default_model="", provider_type="custom")
        assert provider.default_model == ""
        assert provider.provider_type == "custom"

    def test_empty_litellm_model_defaults(self):
        """Default litellm_model is empty string when not provided."""
        provider = ProviderCreate(name="My LLM")
        assert provider.default_model == ""

    def test_litellm_model_too_long_rejected(self):
        with pytest.raises(ValidationError):
            ProviderCreate(name="My LLM", default_model="a" * 256)


class TestProviderUpdate:
    def test_all_fields_optional(self):
        update = ProviderUpdate()
        assert update.name is None
        assert update.default_model is None
        assert update.api_base is None
        assert update.api_key_env is None
        assert update.proxy is None
        assert update.tags is None

    def test_partial_update(self):
        update = ProviderUpdate(name="New Name")
        assert update.name == "New Name"
        assert update.default_model is None

    def test_empty_name_in_update_rejected(self):
        with pytest.raises(ValidationError):
            ProviderUpdate(name="")

    def test_json_schema_includes_descriptions(self):
        """All ProviderCreate fields must have descriptions for frontend tooltips."""
        schema = ProviderCreate.model_json_schema()
        props = schema["properties"]

        expected_fields = [
            "name",
            "default_model",
            "api_base",
            "api_key_env",
            "proxy",
            "ssl_cert_path",
            "ssl_client_key",
            "tags",
            "default_params",
            "provider_type",
            "endpoint_url",
            "request_body_template",
            "response_json_path",
        ]

        for field_name in expected_fields:
            assert field_name in props, f"Field {field_name} missing from schema"
            field_schema = props[field_name]
            # Some optional fields use anyOf; description may be on the top level
            desc = field_schema.get("description")
            if desc is None and "anyOf" in field_schema:
                # For Optional[str] fields, Pydantic puts description at the top level
                desc = field_schema.get("description")
            assert desc, f"Field {field_name} is missing a description in the JSON schema"
            assert len(desc) > 10, f"Field {field_name} description is too short: {desc!r}"


class TestProviderResponse:
    def test_from_attributes(self):
        assert ProviderResponse.model_config.get("from_attributes") is True

    def test_defaults(self):
        resp = ProviderResponse(id="p-1", name="Test", default_model="m")
        assert resp.has_api_key is False
        assert resp.tags == []
