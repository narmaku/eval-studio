"""Base classes for RAG backend adapters."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


@dataclass
class RAGResponse:
    """Response from a RAG backend containing the generated answer and retrieved chunks."""

    answer: str
    chunks: list[dict[str, Any]] = field(default_factory=list)


def normalize_chunks(raw_chunks: list[Any]) -> list[dict[str, Any]]:
    """Normalize chunks to a list of dicts, each containing at least a 'content' key.

    Handles:
    - list of dicts (pass through, ensure 'content' key exists)
    - list of strings (wrap each in {"content": str})
    """
    normalized: list[dict[str, Any]] = []
    for chunk in raw_chunks:
        if isinstance(chunk, dict):
            if "content" not in chunk:
                # Try common alternatives
                text = chunk.get("text") or chunk.get("page_content") or str(chunk)
                chunk = {**chunk, "content": text}
            normalized.append(chunk)
        elif isinstance(chunk, str):
            normalized.append({"content": chunk})
        else:
            normalized.append({"content": str(chunk)})
    return normalized


class RAGBackendAdapter(ABC):
    """Abstract base class for RAG backend adapters.

    Each adapter encapsulates the logic to send a question to a RAG system
    and return the generated answer along with retrieved context chunks.
    """

    @abstractmethod
    async def retrieve_and_generate(self, question: str) -> RAGResponse:
        """Send a question to the RAG backend and return answer + retrieved chunks."""
        ...

    @abstractmethod
    async def health_check(self) -> bool:
        """Check if the RAG backend is reachable."""
        ...

    async def close(self) -> None:
        """Release resources held by the adapter (no-op by default)."""
        return
