"""add_rate_limit_fields_to_providers

Revision ID: 3fc49606c57f
Revises: a3b4c5d6e7f8
Create Date: 2026-06-09 15:21:19.274464

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "3fc49606c57f"
down_revision: str | None = "a3b4c5d6e7f8"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("providers", schema=None) as batch_op:
        batch_op.add_column(sa.Column("rate_limited", sa.Boolean(), nullable=False, server_default=sa.text("0")))
        batch_op.add_column(sa.Column("rate_limits", sa.JSON(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("providers", schema=None) as batch_op:
        batch_op.drop_column("rate_limits")
        batch_op.drop_column("rate_limited")
