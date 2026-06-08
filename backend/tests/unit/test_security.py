"""Unit tests for security helper functions."""

from app.core.security import API_KEY_PREFIX, generate_api_key, hash_api_key


def test_generate_api_key_has_prefix():
    """Generated keys start with the ``esk_`` prefix."""
    key = generate_api_key()
    assert key.startswith(API_KEY_PREFIX)


def test_generate_api_key_sufficient_length():
    """Generated keys have at least 32 characters total."""
    key = generate_api_key()
    assert len(key) > 32


def test_generate_api_key_unique():
    """Successive calls produce different keys."""
    keys = {generate_api_key() for _ in range(20)}
    assert len(keys) == 20


def test_hash_api_key_consistent():
    """The same input always produces the same SHA-256 hash."""
    raw = "esk_test-key-123"
    h1 = hash_api_key(raw)
    h2 = hash_api_key(raw)
    assert h1 == h2


def test_hash_api_key_is_hex_digest():
    """Hash output is a 64-character hexadecimal string."""
    h = hash_api_key("esk_anything")
    assert len(h) == 64
    assert all(c in "0123456789abcdef" for c in h)


def test_hash_api_key_different_inputs():
    """Different inputs produce different hashes."""
    h1 = hash_api_key("esk_key-one")
    h2 = hash_api_key("esk_key-two")
    assert h1 != h2
