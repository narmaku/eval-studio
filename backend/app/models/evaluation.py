from datetime import datetime

from sqlalchemy import JSON, DateTime, Float, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.core.database import utcnow as _utcnow


class Evaluation(Base):
    __tablename__ = "evaluations"

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    mode: Mapped[str] = mapped_column(String(50), nullable=False)
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="pending")
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    config: Mapped[dict | None] = mapped_column(JSON, nullable=True, default=dict)
    dataset_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    judge_config_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow, onupdate=_utcnow)

    results: Mapped[list["Result"]] = relationship(
        "Result", back_populates="evaluation", cascade="all, delete-orphan", lazy="selectin"
    )
    sessions: Mapped[list["Session"]] = relationship("Session", back_populates="evaluation", lazy="selectin")
    artifacts: Mapped[list["Artifact"]] = relationship(
        "Artifact", back_populates="evaluation", cascade="all, delete-orphan", lazy="selectin"
    )


class JudgeConfig(Base):
    __tablename__ = "judge_configs"

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    preset: Mapped[str | None] = mapped_column(String(50), nullable=True)
    model: Mapped[str | None] = mapped_column(String(255), nullable=True)
    temperature: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    prompt_template: Mapped[str | None] = mapped_column(Text, nullable=True)
    pass_threshold: Mapped[float] = mapped_column(Float, nullable=False, default=0.7)
    dimensions: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    aggregation: Mapped[str | None] = mapped_column(String(50), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow, onupdate=_utcnow)


# Avoid circular import: import at module level after class definitions
from app.models.artifact import Artifact  # noqa: E402
from app.models.result import Result  # noqa: E402
from app.models.session import Session  # noqa: E402
