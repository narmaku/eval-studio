"""HTTP-based RAG backend adapter.

Sends questions to a RAG service over HTTP and extracts answers and context
chunks from the JSON response. Refactored from inline httpx code that was
previously in rag_evaluation_service.py.
"""

import logging
from typing import Any

import httpx

from app.rag_backends.base import RAGBackendAdapter, RAGResponse, normalize_chunks

logger = logging.getLogger(__name__)


class HttpRAGAdapter(RAGBackendAdapter):
    """RAG backend adapter that communicates with a RAG service via HTTP POST."""

    def __init__(
        self,
        url: str,
        auth_header: dict[str, str] | None = None,
        query_field: str = "query",
        answer_field: str = "answer",
        chunks_field: str = "source_documents",
        timeout: float = 60.0,
    ) -> None:
        self.url = url
        self.auth_header = auth_header
        self.query_field = query_field
        self.answer_field = answer_field
        self.chunks_field = chunks_field
        self.timeout = timeout
        self._client: httpx.AsyncClient | None = None

    async def _get_client(self) -> httpx.AsyncClient:
        """Return a shared httpx client, creating one if needed."""
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(timeout=self.timeout)
        return self._client

    async def retrieve_and_generate(self, question: str) -> RAGResponse:
        """POST the question to the RAG endpoint and parse the response."""
        client = await self._get_client()

        headers: dict[str, str] = {}
        if self.auth_header:
            headers.update(self.auth_header)

        request_body: dict[str, Any] = {self.query_field: question}
        response = await client.post(self.url, json=request_body, headers=headers)
        response.raise_for_status()
        response_json = response.json()

        answer = response_json.get(self.answer_field, "")
        raw_chunks = response_json.get(self.chunks_field, [])
        chunks = normalize_chunks(raw_chunks)

        return RAGResponse(answer=answer, chunks=chunks)

    async def health_check(self) -> bool:
        """GET the RAG endpoint URL and return True if the status is 2xx."""
        try:
            client = await self._get_client()
            response = await client.get(self.url)
            return 200 <= response.status_code < 300
        except Exception:
            logger.debug("Health check failed for %s", self.url, exc_info=True)
            return False

    async def close(self) -> None:
        """Close the underlying HTTP client."""
        if self._client and not self._client.is_closed:
            await self._client.aclose()
            self._client = None
