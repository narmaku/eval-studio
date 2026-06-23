"""drop judge_configs table and judge_config_id FK

Revision ID: cea91902da6d
Revises: eccd117143f3
Create Date: 2026-06-23 11:03:42.907729

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "cea91902da6d"
down_revision: str | None = "eccd117143f3"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("evaluations", schema=None) as batch_op:
        batch_op.drop_column("judge_config_id")

    op.drop_table("judge_configs")


def downgrade() -> None:
    op.create_table(
        "judge_configs",
        sa.Column("name", sa.VARCHAR(length=255), nullable=False),
        sa.Column("preset", sa.VARCHAR(length=50), nullable=True),
        sa.Column("model", sa.VARCHAR(length=255), nullable=True),
        sa.Column("temperature", sa.FLOAT(), nullable=False),
        sa.Column("prompt_template", sa.TEXT(), nullable=True),
        sa.Column("pass_threshold", sa.FLOAT(), nullable=False),
        sa.Column("dimensions", sa.JSON(), nullable=True),
        sa.Column("aggregation", sa.VARCHAR(length=50), nullable=True),
        sa.Column("updated_at", sa.DATETIME(), nullable=False),
        sa.Column("id", sa.VARCHAR(length=36), nullable=False),
        sa.Column("created_at", sa.DATETIME(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )

    with op.batch_alter_table("evaluations", schema=None) as batch_op:
        batch_op.add_column(sa.Column("judge_config_id", sa.VARCHAR(length=36), nullable=True))
