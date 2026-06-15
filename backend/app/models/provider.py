"""Provider ORM model for storing user-created inference provider profiles."""

from datetime import datetime

from sqlalchemy import JSON, DateTime, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.core.database import utcnow as _utcnow


class Provider(Base):
    __tablename__ = "providers"

    name: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    default_model: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    api_base: Mapped[str | None] = mapped_column(String(512), nullable=True)
    api_key_env: Mapped[str | None] = mapped_column(String(255), nullable=True)
    proxy: Mapped[str | None] = mapped_column(String(512), nullable=True)
    ssl_cert_path: Mapped[str | None] = mapped_column(String(512), nullable=True)
    ssl_client_key: Mapped[str | None] = mapped_column(String(512), nullable=True)
    tags: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    source: Mapped[str] = mapped_column(String(50), nullable=False, default="user")
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow, onupdate=_utcnow)
    provider_type: Mapped[str] = mapped_column(String(50), nullable=False, default="litellm")
    endpoint_url: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    request_body_template: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    response_json_path: Mapped[str] = mapped_column(String(255), nullable=False, default="choices.0.message.content")
    single_model: Mapped[bool] = mapped_column(default=False)
    rate_limited: Mapped[bool] = mapped_column(default=False)
    rate_limits: Mapped[list | None] = mapped_column(JSON, nullable=True, default=None)
