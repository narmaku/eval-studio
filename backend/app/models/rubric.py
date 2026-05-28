"""Rubric ORM model for storing reusable scoring criteria."""

from datetime import UTC, datetime

from sqlalchemy import JSON, DateTime, Float, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


def _utcnow() -> datetime:
    return datetime.now(UTC)


class Rubric(Base):
    __tablename__ = "rubrics"

    name: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    dimensions: Mapped[list] = mapped_column(JSON, nullable=False)
    pass_threshold: Mapped[float] = mapped_column(Float, nullable=False, default=0.7)
    aggregation: Mapped[str] = mapped_column(String(50), nullable=False, default="weighted_average")
    prompt_template: Mapped[str | None] = mapped_column(Text, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow, onupdate=_utcnow)
