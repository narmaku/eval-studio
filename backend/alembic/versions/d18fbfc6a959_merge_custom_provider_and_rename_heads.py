"""merge custom provider and rename heads

Revision ID: d18fbfc6a959
Revises: 416da1255d27, a1b2c3d4e5f6
Create Date: 2026-06-08 12:31:19.853192

"""

from collections.abc import Sequence

# revision identifiers, used by Alembic.
revision: str = "d18fbfc6a959"
down_revision: str | None = ("416da1255d27", "a1b2c3d4e5f6")
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
