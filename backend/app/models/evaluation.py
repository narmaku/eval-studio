from datetime import datetime

from sqlalchemy import JSON, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base, TZDateTime
from app.core.database import utcnow as _utcnow


class Evaluation(Base):
    __tablename__ = "evaluations"

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    mode: Mapped[str] = mapped_column(String(50), nullable=False)
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="pending")
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    config: Mapped[dict | None] = mapped_column(JSON, nullable=True, default=dict)
    tags: Mapped[list | None] = mapped_column(JSON, nullable=True, default=list)
    user_metadata: Mapped[dict | None] = mapped_column("metadata", JSON, nullable=True, default=dict)
    dataset_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("datasets.id", ondelete="RESTRICT"), nullable=True
    )
    rubric_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("rubrics.id", ondelete="SET NULL"), nullable=True
    )
    updated_at: Mapped[datetime] = mapped_column(TZDateTime, default=_utcnow, onupdate=_utcnow)

    results: Mapped[list["Result"]] = relationship(
        "Result", back_populates="evaluation", cascade="all, delete-orphan", passive_deletes=True, lazy="raise"
    )
    sessions: Mapped[list["Session"]] = relationship(
        "Session", back_populates="evaluation", passive_deletes=True, lazy="raise"
    )
    artifacts: Mapped[list["Artifact"]] = relationship(
        "Artifact", back_populates="evaluation", cascade="all, delete-orphan", passive_deletes=True, lazy="raise"
    )


# Avoid circular import: import at module level after class definitions
from app.models.artifact import Artifact  # noqa: E402
from app.models.result import Result  # noqa: E402
from app.models.session import Session  # noqa: E402
