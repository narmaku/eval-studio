"""migrate_scored_sessions_data

Revision ID: f25d781af937
Revises: 346b00c58bbe
Create Date: 2026-06-15 18:08:56.924647

"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "f25d781af937"
down_revision: str | None = "346b00c58bbe"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        "UPDATE sessions SET status = 'completed' "
        "WHERE status = 'ended' AND scores IS NOT NULL AND scores != 'null' AND length(scores) > 4"
    )


def downgrade() -> None:
    pass
