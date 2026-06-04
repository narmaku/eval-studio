"""PgVector-based RAG backend adapter.

Retrieves context chunks directly from a PostgreSQL database with pgvector,
generates embeddings via LiteLLM, and produces an answer using an LLM.
"""

from typing import Any

import structlog

from app.rag_backends.base import RAGBackendAdapter, RAGResponse

logger = structlog.get_logger()

try:
    import asyncpg
except ImportError:
    asyncpg = None  # type: ignore[assignment]


class PgVectorRAGAdapter(RAGBackendAdapter):
    """RAG backend adapter that queries pgvector directly and generates via LiteLLM."""

    def __init__(
        self,
        connection_string: str,
        table_name: str,
        embedding_column: str = "embedding",
        content_column: str = "content",
        top_k: int = 5,
        generator_model: str = "gpt-3.5-turbo",
        generator_api_key: str | None = None,
        generator_api_base: str | None = None,
        embedding_model: str = "text-embedding-3-small",
    ) -> None:
        if asyncpg is None:
            raise ImportError(
                "asyncpg is required for PgVectorRAGAdapter. Install it with: uv add asyncpg  or  pip install asyncpg"
            )

        self.connection_string = connection_string
        self.table_name = table_name
        self.embedding_column = embedding_column
        self.content_column = content_column
        self.top_k = top_k
        self.generator_model = generator_model
        self.generator_api_key = generator_api_key
        self.generator_api_base = generator_api_base
        self.embedding_model = embedding_model

    async def retrieve_and_generate(self, question: str) -> RAGResponse:
        """Generate embedding, query pgvector, build context, and generate answer."""
        import litellm

        # Step 1: Generate embedding for the question
        embedding_response = await litellm.aembedding(
            model=self.embedding_model,
            input=[question],
        )
        embedding = embedding_response.data[0]["embedding"]
        embedding_str = "[" + ",".join(str(v) for v in embedding) + "]"

        # Step 2: Query pgvector for similar chunks
        conn = await asyncpg.connect(self.connection_string)
        try:
            query = (
                f"SELECT {self.content_column}, "
                f"1 - ({self.embedding_column} <=> $1::vector) as relevance "
                f"FROM {self.table_name} "
                f"ORDER BY {self.embedding_column} <=> $1::vector "
                f"LIMIT {self.top_k}"
            )
            rows = await conn.fetch(query, embedding_str)
        finally:
            await conn.close()

        # Step 3: Build context from retrieved chunks
        chunks: list[dict[str, Any]] = []
        context_parts: list[str] = []
        for row in rows:
            content = row[self.content_column]
            relevance = float(row["relevance"])
            chunks.append({"content": content, "relevance_score": relevance})
            context_parts.append(content)

        context = "\n\n".join(context_parts)

        # Step 4: Generate answer using LiteLLM
        generation_kwargs: dict[str, Any] = {
            "model": self.generator_model,
            "messages": [
                {
                    "role": "user",
                    "content": (
                        f"Based on the following context, answer the question: {question}\n\nContext:\n{context}"
                    ),
                }
            ],
        }
        if self.generator_api_key:
            generation_kwargs["api_key"] = self.generator_api_key
        if self.generator_api_base:
            generation_kwargs["api_base"] = self.generator_api_base

        gen_response = await litellm.acompletion(**generation_kwargs)
        answer = gen_response.choices[0].message.content or ""

        return RAGResponse(answer=answer, chunks=chunks)

    async def health_check(self) -> bool:
        """Try connecting to the PostgreSQL database."""
        try:
            conn = await asyncpg.connect(self.connection_string)
            await conn.close()
            return True
        except Exception:
            logger.debug("rag_pgvector.health_check_failed", exc_info=True)
            return False
