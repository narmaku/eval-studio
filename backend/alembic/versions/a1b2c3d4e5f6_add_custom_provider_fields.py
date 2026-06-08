"""add custom provider fields

Revision ID: a1b2c3d4e5f6
Revises: 2a778187e3d6, 417963dff6f8
Create Date: 2026-06-08 12:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "a1b2c3d4e5f6"
down_revision: tuple[str, ...] = ("2a778187e3d6", "417963dff6f8")
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("providers", schema=None) as batch_op:
        batch_op.add_column(sa.Column("provider_type", sa.String(length=50), nullable=False, server_default="litellm"))
        batch_op.add_column(sa.Column("endpoint_url", sa.String(length=1024), nullable=True))
        batch_op.add_column(sa.Column("request_format", sa.String(length=50), nullable=False, server_default="openai"))
        batch_op.add_column(
            sa.Column(
                "response_json_path",
                sa.String(length=255),
                nullable=False,
                server_default="choices.0.message.content",
            )
        )


def downgrade() -> None:
    with op.batch_alter_table("providers", schema=None) as batch_op:
        batch_op.drop_column("response_json_path")
        batch_op.drop_column("request_format")
        batch_op.drop_column("endpoint_url")
        batch_op.drop_column("provider_type")
