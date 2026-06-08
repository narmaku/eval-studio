"""drop purpose from providers

Revision ID: a3b4c5d6e7f8
Revises: f76f799797d6
Create Date: 2026-06-09 07:30:00.000000

"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "a3b4c5d6e7f8"
down_revision: str | None = "f76f799797d6"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("providers") as batch_op:
        batch_op.drop_column("purpose")


def downgrade() -> None:
    import sqlalchemy as sa

    with op.batch_alter_table("providers") as batch_op:
        batch_op.add_column(sa.Column("purpose", sa.String(50), nullable=False, server_default="test"))
