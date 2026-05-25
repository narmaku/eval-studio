from sqlalchemy import JSON, Boolean, Float, ForeignKey, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class Result(Base):
    __tablename__ = "results"

    evaluation_id: Mapped[str] = mapped_column(String(36), ForeignKey("evaluations.id"), nullable=False, index=True)
    dataset_item_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("dataset_items.id"), nullable=True)
    session_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("sessions.id"), nullable=True)
    score: Mapped[float | None] = mapped_column(Float, nullable=True)
    passed: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    actual_answer: Mapped[str | None] = mapped_column(Text, nullable=True)
    judge_reasoning: Mapped[str | None] = mapped_column(Text, nullable=True)
    scores_breakdown: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    evaluation: Mapped["Evaluation"] = relationship("Evaluation", back_populates="results")  # noqa: F821

    __table_args__ = (Index("ix_results_eval_score_created", "evaluation_id", "score", "created_at"),)
