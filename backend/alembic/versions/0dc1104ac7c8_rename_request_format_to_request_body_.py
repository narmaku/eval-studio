"""rename request_format to request_body_template

Revision ID: 0dc1104ac7c8
Revises: d18fbfc6a959
Create Date: 2026-06-08 14:21:55.241170

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0dc1104ac7c8"
down_revision: str | None = "d18fbfc6a959"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("providers") as batch_op:
        batch_op.alter_column(
            "request_format", new_column_name="request_body_template", type_=sa.String(1024), nullable=True
        )


def downgrade() -> None:
    with op.batch_alter_table("providers") as batch_op:
        batch_op.alter_column(
            "request_body_template", new_column_name="request_format", type_=sa.String(50), nullable=False
        )
