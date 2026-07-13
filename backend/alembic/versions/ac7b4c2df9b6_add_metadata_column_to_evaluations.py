"""add metadata column to evaluations

Revision ID: ac7b4c2df9b6
Revises: 0251a906d547
Create Date: 2026-07-13 16:04:36.443695

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "ac7b4c2df9b6"
down_revision: str | None = "0251a906d547"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("evaluations", schema=None) as batch_op:
        batch_op.add_column(sa.Column("metadata", sa.JSON(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("evaluations", schema=None) as batch_op:
        batch_op.drop_column("metadata")
