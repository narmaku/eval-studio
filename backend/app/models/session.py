from datetime import UTC, datetime

from sqlalchemy import JSON, DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


def _utcnow() -> datetime:
    return datetime.now(UTC)


class Session(Base):
    __tablename__ = "sessions"

    evaluation_id: Mapped[str] = mapped_column(String(36), ForeignKey("evaluations.id"), nullable=False)
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="active")
    mode: Mapped[str] = mapped_column(String(50), nullable=False, default="live")
    transcript: Mapped[list | None] = mapped_column(JSON, nullable=True, default=list)
    agent_config: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    judge_config_snapshot: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    scores: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, default=_utcnow)
    ended_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    evaluation: Mapped["Evaluation"] = relationship("Evaluation", back_populates="sessions")  # noqa: F821
