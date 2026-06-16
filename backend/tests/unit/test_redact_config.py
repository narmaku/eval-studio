"""Tests for config secret redaction utility."""

from app.core.security import redact_config

REDACTED = "**REDACTED**"


class TestRedactConfig:
    """redact_config masks values whose keys match secret patterns."""

    def test_masks_auth_header(self):
        config = {"auth_header": {"Authorization": "Bearer secret-token"}, "url": "http://example.com"}
        result = redact_config(config)
        assert result["auth_header"] == REDACTED
        assert result["url"] == "http://example.com"

    def test_masks_auth_token_env(self):
        config = {"auth_token_env": "MY_TOKEN_VAR", "url": "http://example.com"}
        result = redact_config(config)
        assert result["auth_token_env"] == REDACTED

    def test_masks_api_key_variants(self):
        config = {"generator_api_key": "sk-abc123", "api_key_env": "API_KEY_VAR"}
        result = redact_config(config)
        assert result["generator_api_key"] == REDACTED
        assert result["api_key_env"] == REDACTED

    def test_masks_connection_string(self):
        config = {"connection_string": "postgresql://user:pass@host:5432/db"}
        result = redact_config(config)
        assert result["connection_string"] == REDACTED

    def test_masks_password_and_secret(self):
        config = {"db_password": "hunter2", "jwt_secret": "my-secret"}
        result = redact_config(config)
        assert result["db_password"] == REDACTED
        assert result["jwt_secret"] == REDACTED

    def test_preserves_non_secret_keys(self):
        config = {"url": "http://example.com", "query_field": "query", "top_k": 5, "backend_type": "http"}
        result = redact_config(config)
        assert result == config

    def test_case_insensitive_matching(self):
        config = {"Auth_Header": "Bearer token", "CONNECTION_STRING": "pg://..."}
        result = redact_config(config)
        assert result["Auth_Header"] == REDACTED
        assert result["CONNECTION_STRING"] == REDACTED

    def test_empty_config(self):
        assert redact_config({}) == {}

    def test_nested_rag_endpoint(self):
        config = {
            "rag_endpoint": {
                "url": "http://rag.example.com",
                "auth_header": {"Authorization": "Bearer secret"},
            },
            "model_endpoint": {"provider_id": "openai", "name": "gpt-4"},
        }
        result = redact_config(config)
        assert result["rag_endpoint"]["auth_header"] == REDACTED
        assert result["rag_endpoint"]["url"] == "http://rag.example.com"
        assert result["model_endpoint"] == config["model_endpoint"]

    def test_does_not_mutate_original(self):
        config = {"auth_header": "Bearer secret", "url": "http://example.com"}
        redact_config(config)
        assert config["auth_header"] == "Bearer secret"

    def test_skips_none_values(self):
        config = {"auth_header": None, "url": "http://example.com"}
        result = redact_config(config)
        assert result["auth_header"] is None
