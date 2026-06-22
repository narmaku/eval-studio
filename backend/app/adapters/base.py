import asyncio
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass
class Score:
    """Result of scoring an evaluation item."""

    value: float  # 0.0 to 1.0
    passed: bool
    reasoning: str | None = None
    breakdown: dict[str, float] | None = None


@dataclass
class Message:
    """A single message in a conversation."""

    role: str  # "user", "assistant", "system"
    content: str
    timestamp: datetime | None = None


@dataclass
class ToolCall:
    """A tool/function call made during a conversation."""

    tool_name: str
    arguments: dict[str, Any] = field(default_factory=dict)
    result: str | None = None
    duration_ms: int | None = None


@dataclass
class JudgeConfigParams:
    """Parameters for judge configuration used by adapters.

    This is a plain dataclass decoupled from the SQLAlchemy model so that
    adapter code does not depend on the ORM layer.
    """

    model: str | None = None
    temperature: float = 0.0
    prompt_template: str | None = None
    pass_threshold: float = 0.7
    dimensions: list[dict[str, Any]] | None = None
    aggregation: str | None = None


class EvaluationAdapter(ABC):
    """Base interface for evaluation backend adapters."""

    def __init__(self, max_concurrency: int = 10):
        self._semaphore = asyncio.Semaphore(max_concurrency)

    @classmethod
    def get_config_schema(cls) -> dict[str, Any]:
        """Return a JSON Schema describing configurable fields for this adapter.

        Subclasses should override to provide adapter-specific schema.
        """
        return {}

    @abstractmethod
    async def evaluate_qa(
        self,
        question: str,
        expected_answer: str,
        actual_answer: str,
        judge_config: JudgeConfigParams,
    ) -> Score:
        """Score a single Q&A pair."""
        ...

    @abstractmethod
    async def evaluate_conversation(
        self,
        messages: list[Message],
        tool_calls: list[ToolCall],
        judge_config: JudgeConfigParams,
    ) -> Score:
        """Score a multi-turn conversation with tool calls."""
        ...

    @abstractmethod
    async def evaluate_rag(
        self,
        question: str,
        context_chunks: list[str],
        answer: str,
        expected_answer: str | None,
        metrics: list[str],
        judge_config: JudgeConfigParams | None = None,
    ) -> dict[str, Score]:
        """Score a RAG response with retrieved context."""
        ...
