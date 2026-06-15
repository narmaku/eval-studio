"""drop_environments_table_and_environment_id

Revision ID: 346b00c58bbe
Revises: 66b746a633ce
Create Date: 2026-06-15 17:57:43.022907

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "346b00c58bbe"
down_revision: str | None = "66b746a633ce"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.drop_column("evaluations", "environment_id")
    op.drop_table("environments")


def downgrade() -> None:
    op.create_table(
        "environments",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("type", sa.String(50), nullable=False),
        sa.Column("status", sa.String(50), nullable=False, server_default="idle"),
        sa.Column("config", sa.JSON, nullable=True),
        sa.Column("health", sa.JSON, nullable=True),
        sa.Column("created_at", sa.DateTime, nullable=True),
        sa.Column("updated_at", sa.DateTime, nullable=True),
    )
    op.add_column("evaluations", sa.Column("environment_id", sa.String(36), nullable=True))
