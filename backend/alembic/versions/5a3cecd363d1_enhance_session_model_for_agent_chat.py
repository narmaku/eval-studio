"""enhance session model for agent chat

Revision ID: 5a3cecd363d1
Revises: 92f2dd645ebe
Create Date: 2026-05-26 16:27:53.464381

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "5a3cecd363d1"
down_revision: str | None = "92f2dd645ebe"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("sessions", schema=None) as batch_op:
        batch_op.add_column(sa.Column("mode", sa.String(length=50), nullable=False, server_default="live"))
        batch_op.add_column(sa.Column("agent_config", sa.JSON(), nullable=True))
        batch_op.add_column(sa.Column("judge_config_snapshot", sa.JSON(), nullable=True))
        batch_op.add_column(sa.Column("scores", sa.JSON(), nullable=True))
        batch_op.add_column(sa.Column("error", sa.Text(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("sessions", schema=None) as batch_op:
        batch_op.drop_column("error")
        batch_op.drop_column("scores")
        batch_op.drop_column("judge_config_snapshot")
        batch_op.drop_column("agent_config")
        batch_op.drop_column("mode")
