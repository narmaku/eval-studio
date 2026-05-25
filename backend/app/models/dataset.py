from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, ForeignKey, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Dataset(Base):
    __tablename__ = "datasets"

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    format: Mapped[str] = mapped_column(String(50), nullable=False, default="qa_pairs")
    version: Mapped[str] = mapped_column(String(50), nullable=False, default="1.0")
    tags: Mapped[dict | None] = mapped_column(JSON, nullable=True, default=list)
    source_type: Mapped[str] = mapped_column(String(50), nullable=False, default="upload")
    item_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow, onupdate=_utcnow)

    items: Mapped[list["DatasetItem"]] = relationship(
        "DatasetItem", back_populates="dataset", cascade="all, delete-orphan", lazy="selectin"
    )


class DatasetItem(Base):
    __tablename__ = "dataset_items"

    dataset_id: Mapped[str] = mapped_column(String(36), ForeignKey("datasets.id"), nullable=False, index=True)
    question: Mapped[str] = mapped_column(Text, nullable=False)
    expected_answer: Mapped[str | None] = mapped_column(Text, nullable=True)
    metadata_: Mapped[dict | None] = Column("metadata", JSON, nullable=True)
    order_index: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    dataset: Mapped["Dataset"] = relationship("Dataset", back_populates="items")
