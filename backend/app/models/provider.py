"""Provider ORM model for storing user-created inference provider profiles."""

from datetime import UTC, datetime

from sqlalchemy import JSON, DateTime, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


def _utcnow() -> datetime:
    return datetime.now(UTC)


class Provider(Base):
    __tablename__ = "providers"

    name: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    litellm_model: Mapped[str] = mapped_column(String(255), nullable=False)
    api_base: Mapped[str | None] = mapped_column(String(512), nullable=True)
    api_key_env: Mapped[str | None] = mapped_column(String(255), nullable=True)
    proxy: Mapped[str | None] = mapped_column(String(512), nullable=True)
    tags: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    purpose: Mapped[str] = mapped_column(String(50), nullable=False, default="test")
    source: Mapped[str] = mapped_column(String(50), nullable=False, default="user")
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow, onupdate=_utcnow)
