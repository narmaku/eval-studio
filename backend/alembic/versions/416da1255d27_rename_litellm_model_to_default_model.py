"""rename litellm_model to default_model

Revision ID: 416da1255d27
Revises: ba5ca10b45b6
Create Date: 2026-06-08 11:48:45.410888

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '416da1255d27'
down_revision: Union[str, None] = 'ba5ca10b45b6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("providers") as batch_op:
        batch_op.alter_column("litellm_model", new_column_name="default_model", nullable=True)


def downgrade() -> None:
    with op.batch_alter_table("providers") as batch_op:
        batch_op.alter_column("default_model", new_column_name="litellm_model", nullable=False)
