from typing import Generic, TypeVar

from pydantic import BaseModel

T = TypeVar("T")


class PaginatedResponse(BaseModel, Generic[T]):
    """Generic paginated response envelope.

    Convention: DB-backed collections use ``PaginatedResponse``; bounded
    config/registry collections (providers, harnesses, tool-servers,
    evaluators, judge presets) return bare JSON arrays.
    """

    items: list[T]
    total: int
    page: int
    page_size: int
    pages: int


class ProblemDetail(BaseModel):
    """RFC 7807 Problem Details for HTTP APIs."""

    type: str = "about:blank"
    title: str
    status: int
    detail: str
    instance: str | None = None
    errors: list[dict] | None = None
