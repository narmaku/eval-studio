"""add_rubric_id_to_evaluations

Revision ID: eccd117143f3
Revises: f1a3fd8cc116
Create Date: 2026-06-22 18:18:49.744027

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "eccd117143f3"
down_revision: str | None = "f1a3fd8cc116"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("evaluations", schema=None) as batch_op:
        batch_op.add_column(sa.Column("rubric_id", sa.String(length=36), nullable=True))
        batch_op.create_foreign_key("fk_evaluations_rubric_id", "rubrics", ["rubric_id"], ["id"], ondelete="SET NULL")


def downgrade() -> None:
    with op.batch_alter_table("evaluations", schema=None) as batch_op:
        batch_op.drop_constraint("fk_evaluations_rubric_id", type_="foreignkey")
        batch_op.drop_column("rubric_id")
