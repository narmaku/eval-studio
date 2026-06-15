"""drop_providers_table

The YAML-backed provider registry is the single source of truth.
The SQLAlchemy Provider model and its DB table are unused dead code
(ARCH-002). Drop the table; existing rows are abandoned.

Revision ID: 66b746a633ce
Revises: 1307fd3f3b27
Create Date: 2026-06-15 17:04:18.484432

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "66b746a633ce"
down_revision: str | None = "1307fd3f3b27"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.drop_table("providers")


def downgrade() -> None:
    op.create_table(
        "providers",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("name", sa.String(255), unique=True, nullable=False),
        sa.Column("default_model", sa.String(255), nullable=False, server_default=""),
        sa.Column("api_base", sa.String(512), nullable=True),
        sa.Column("api_key_env", sa.String(255), nullable=True),
        sa.Column("proxy", sa.String(512), nullable=True),
        sa.Column("ssl_cert_path", sa.String(512), nullable=True),
        sa.Column("ssl_client_key", sa.String(512), nullable=True),
        sa.Column("tags", sa.JSON, nullable=False, server_default="[]"),
        sa.Column("source", sa.String(50), nullable=False, server_default="user"),
        sa.Column("updated_at", sa.DateTime, nullable=True),
        sa.Column("provider_type", sa.String(50), nullable=False, server_default="litellm"),
        sa.Column("endpoint_url", sa.String(1024), nullable=True),
        sa.Column("request_body_template", sa.String(1024), nullable=True),
        sa.Column("response_json_path", sa.String(255), nullable=False, server_default="choices.0.message.content"),
        sa.Column("single_model", sa.Boolean, server_default="0"),
        sa.Column("rate_limited", sa.Boolean, server_default="0"),
        sa.Column("rate_limits", sa.JSON, nullable=True),
    )
