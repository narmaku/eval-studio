"""Rubric ORM model for storing reusable scoring criteria."""

from datetime import datetime

from sqlalchemy import JSON, Float, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base, TZDateTime
from app.core.database import utcnow as _utcnow


class Rubric(Base):
    __tablename__ = "rubrics"

    name: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    dimensions: Mapped[list] = mapped_column(JSON, nullable=False)
    pass_threshold: Mapped[float] = mapped_column(Float, nullable=False, default=0.7)
    aggregation: Mapped[str] = mapped_column(String(50), nullable=False, default="weighted_average")
    prompt_template: Mapped[str | None] = mapped_column(Text, nullable=True)
    tags: Mapped[list | None] = mapped_column(JSON, nullable=True, default=list)
    updated_at: Mapped[datetime] = mapped_column(TZDateTime, default=_utcnow, onupdate=_utcnow)
