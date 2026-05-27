"""Unit tests for the PgVector RAG backend adapter."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

try:
    import asyncpg  # noqa: F401

    HAS_ASYNCPG = True
except ImportError:
    HAS_ASYNCPG = False

pytestmark = pytest.mark.skipif(not HAS_ASYNCPG, reason="asyncpg not installed")


@pytest.fixture
def adapter():
    """Create a PgVectorRAGAdapter with test settings."""
    from app.rag_backends.pgvector_adapter import PgVectorRAGAdapter

    return PgVectorRAGAdapter(
        connection_string="postgresql://test:test@localhost:5432/testdb",
        table_name="documents",
        embedding_column="embedding",
        content_column="content",
        top_k=3,
        generator_model="gpt-3.5-turbo",
        generator_api_key="test-key",
    )


@pytest.mark.asyncio
async def test_retrieve_and_generate_success(adapter):
    """Successful retrieval from pgvector returns answer and chunks with relevance scores."""
    # Mock embedding response
    mock_embedding_response = MagicMock()
    mock_embedding_response.data = [{"embedding": [0.1, 0.2, 0.3]}]

    # Mock DB rows
    mock_row_1 = {"content": "RHEL is Red Hat Enterprise Linux.", "relevance": 0.95}
    mock_row_2 = {"content": "It is enterprise-grade.", "relevance": 0.87}
    mock_rows = [mock_row_1, mock_row_2]

    # Mock generation response
    mock_gen_response = MagicMock()
    mock_gen_response.choices = [MagicMock(message=MagicMock(content="Red Hat Enterprise Linux"))]

    # Mock asyncpg connection
    mock_conn = AsyncMock()
    mock_conn.fetch = AsyncMock(return_value=mock_rows)

    with (
        patch("litellm.aembedding", new_callable=AsyncMock, return_value=mock_embedding_response),
        patch("litellm.acompletion", new_callable=AsyncMock, return_value=mock_gen_response),
        patch("asyncpg.connect", new_callable=AsyncMock, return_value=mock_conn),
    ):
        result = await adapter.retrieve_and_generate("What is RHEL?")

    assert result.answer == "Red Hat Enterprise Linux"
    assert len(result.chunks) == 2
    assert result.chunks[0]["content"] == "RHEL is Red Hat Enterprise Linux."
    assert result.chunks[0]["relevance_score"] == 0.95
    assert result.chunks[1]["content"] == "It is enterprise-grade."
    assert result.chunks[1]["relevance_score"] == 0.87


@pytest.mark.asyncio
async def test_retrieve_and_generate_no_results(adapter):
    """Empty DB returns empty chunks but still generates an answer."""
    # Mock embedding response
    mock_embedding_response = MagicMock()
    mock_embedding_response.data = [{"embedding": [0.1, 0.2, 0.3]}]

    # Mock DB rows - empty
    mock_rows: list = []

    # Mock generation response (still generates even without context)
    mock_gen_response = MagicMock()
    mock_gen_response.choices = [MagicMock(message=MagicMock(content="I don't have enough context to answer."))]

    # Mock asyncpg connection
    mock_conn = AsyncMock()
    mock_conn.fetch = AsyncMock(return_value=mock_rows)

    with (
        patch("litellm.aembedding", new_callable=AsyncMock, return_value=mock_embedding_response),
        patch("litellm.acompletion", new_callable=AsyncMock, return_value=mock_gen_response),
        patch("asyncpg.connect", new_callable=AsyncMock, return_value=mock_conn),
    ):
        result = await adapter.retrieve_and_generate("Unknown question?")

    assert result.answer == "I don't have enough context to answer."
    assert len(result.chunks) == 0


@pytest.mark.asyncio
async def test_health_check_success(adapter):
    """Health check returns True when DB connection succeeds."""
    mock_conn = AsyncMock()

    with patch("asyncpg.connect", new_callable=AsyncMock, return_value=mock_conn):
        result = await adapter.health_check()

    assert result is True
    mock_conn.close.assert_called_once()


@pytest.mark.asyncio
async def test_health_check_failure(adapter):
    """Health check returns False when DB connection fails."""
    with patch("asyncpg.connect", new_callable=AsyncMock, side_effect=Exception("Connection refused")):
        result = await adapter.health_check()

    assert result is False
