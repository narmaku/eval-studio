"""Factory for creating RAG backend adapters from configuration dicts."""

from app.rag_backends.base import RAGBackendAdapter


def create_rag_adapter(config: dict) -> RAGBackendAdapter:
    """Create a RAG backend adapter based on the provided configuration.

    Args:
        config: Dictionary with at least a "backend_type" key ("http" or "pgvector")
                plus adapter-specific parameters.

    Returns:
        An initialized RAGBackendAdapter instance.

    Raises:
        ValueError: If the backend_type is unknown.
    """
    backend_type = config.get("backend_type", "http")

    if backend_type == "http":
        from app.rag_backends.http_adapter import HttpRAGAdapter

        return HttpRAGAdapter(
            url=config["url"],
            auth_header=config.get("auth_header"),
            query_field=config.get("query_field", "query"),
            answer_field=config.get("answer_field", "answer"),
            chunks_field=config.get("chunks_field", "source_documents"),
        )
    elif backend_type == "pgvector":
        from app.rag_backends.pgvector_adapter import PgVectorRAGAdapter

        return PgVectorRAGAdapter(
            connection_string=config["connection_string"],
            table_name=config["table_name"],
            embedding_column=config.get("embedding_column", "embedding"),
            content_column=config.get("content_column", "content"),
            top_k=config.get("top_k", 5),
            generator_model=config["generator_model"],
            generator_api_key=config.get("generator_api_key"),
            generator_api_base=config.get("generator_api_base"),
        )
    else:
        raise ValueError(f"Unknown RAG backend type: {backend_type}")
