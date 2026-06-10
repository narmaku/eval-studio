"""add_single_model_to_providers

Revision ID: 1307fd3f3b27
Revises: 3fc49606c57f
Create Date: 2026-06-10 10:03:33.678903

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '1307fd3f3b27'
down_revision: Union[str, None] = '3fc49606c57f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table('providers', schema=None) as batch_op:
        batch_op.add_column(sa.Column('single_model', sa.Boolean(), nullable=False, server_default=sa.text("0")))


def downgrade() -> None:
    with op.batch_alter_table('providers', schema=None) as batch_op:
        batch_op.drop_column('single_model')
