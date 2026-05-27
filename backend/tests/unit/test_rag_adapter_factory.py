"""Unit tests for the RAG adapter factory."""

import pytest

from app.rag_backends.factory import create_rag_adapter
from app.rag_backends.http_adapter import HttpRAGAdapter

try:
    import asyncpg  # noqa: F401

    HAS_ASYNCPG = True
except ImportError:
    HAS_ASYNCPG = False


def test_create_http_adapter():
    """Factory creates HttpRAGAdapter for backend_type='http'."""
    config = {
        "backend_type": "http",
        "url": "http://localhost:8080/api/rag",
        "query_field": "q",
        "answer_field": "ans",
        "chunks_field": "docs",
    }
    adapter = create_rag_adapter(config)
    assert isinstance(adapter, HttpRAGAdapter)
    assert adapter.url == "http://localhost:8080/api/rag"
    assert adapter.query_field == "q"
    assert adapter.answer_field == "ans"
    assert adapter.chunks_field == "docs"


def test_create_http_adapter_default_type():
    """Factory defaults to HTTP when backend_type is not specified."""
    config = {"url": "http://localhost:8080/api/rag"}
    adapter = create_rag_adapter(config)
    assert isinstance(adapter, HttpRAGAdapter)


@pytest.mark.skipif(not HAS_ASYNCPG, reason="asyncpg not installed")
def test_create_pgvector_adapter():
    """Factory creates PgVectorRAGAdapter for backend_type='pgvector'."""
    from app.rag_backends.pgvector_adapter import PgVectorRAGAdapter

    config = {
        "backend_type": "pgvector",
        "connection_string": "postgresql://user:pass@localhost:5432/db",
        "table_name": "documents",
        "embedding_column": "emb",
        "content_column": "text",
        "top_k": 10,
        "generator_model": "gpt-4",
        "generator_api_key": "sk-test",
    }
    adapter = create_rag_adapter(config)
    assert isinstance(adapter, PgVectorRAGAdapter)
    assert adapter.connection_string == "postgresql://user:pass@localhost:5432/db"
    assert adapter.table_name == "documents"
    assert adapter.embedding_column == "emb"
    assert adapter.content_column == "text"
    assert adapter.top_k == 10
    assert adapter.generator_model == "gpt-4"


def test_unknown_backend_type():
    """Factory raises ValueError for unknown backend_type."""
    config = {"backend_type": "elasticsearch"}
    with pytest.raises(ValueError, match="Unknown RAG backend type: elasticsearch"):
        create_rag_adapter(config)
