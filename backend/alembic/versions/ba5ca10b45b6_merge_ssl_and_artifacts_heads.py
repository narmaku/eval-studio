"""merge ssl and artifacts heads

Revision ID: ba5ca10b45b6
Revises: 2a778187e3d6, 417963dff6f8
Create Date: 2026-06-08 11:48:42.032333

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'ba5ca10b45b6'
down_revision: Union[str, None] = ('2a778187e3d6', '417963dff6f8')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
