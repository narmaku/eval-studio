"""add_fk_constraints_on_evaluation_columns

Adds ForeignKey constraints to Evaluation.dataset_id (RESTRICT) and
Evaluation.judge_config_id (SET NULL).  Pre-cleans orphaned references
before creating constraints.

The ORM models also declare ondelete on Result/Artifact/Session FKs, but
those are not migrated here — SQLite batch mode cannot reliably target
individual FKs on multi-FK tables.  The app-level delete handles cleanup
explicitly, and DATA-006 (migration squash) will rebuild all FKs.

Revision ID: 9d2fc61ed930
Revises: b4de93af30b7
Create Date: 2026-06-22 12:37:04.985015

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "9d2fc61ed930"
down_revision: str | None = "b4de93af30b7"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    conn = op.get_bind()

    conn.execute(
        sa.text(
            "UPDATE evaluations SET judge_config_id = NULL "
            "WHERE judge_config_id IS NOT NULL "
            "AND judge_config_id NOT IN (SELECT id FROM judge_configs)"
        )
    )

    orphan_datasets = conn.execute(
        sa.text(
            "SELECT COUNT(*) FROM evaluations "
            "WHERE dataset_id IS NOT NULL "
            "AND dataset_id NOT IN (SELECT id FROM datasets)"
        )
    ).scalar()
    if orphan_datasets:
        conn.execute(
            sa.text(
                "UPDATE evaluations SET dataset_id = NULL "
                "WHERE dataset_id IS NOT NULL "
                "AND dataset_id NOT IN (SELECT id FROM datasets)"
            )
        )

    with op.batch_alter_table("evaluations") as batch_op:
        batch_op.alter_column("dataset_id", existing_type=sa.String(36), nullable=True)
        batch_op.create_foreign_key(
            "fk_evaluations_dataset_id", "datasets", ["dataset_id"], ["id"], ondelete="RESTRICT"
        )
        batch_op.alter_column("judge_config_id", existing_type=sa.String(36), nullable=True)
        batch_op.create_foreign_key(
            "fk_evaluations_judge_config_id", "judge_configs", ["judge_config_id"], ["id"], ondelete="SET NULL"
        )


def downgrade() -> None:
    with op.batch_alter_table("evaluations") as batch_op:
        batch_op.drop_constraint("fk_evaluations_judge_config_id", type_="foreignkey")
        batch_op.drop_constraint("fk_evaluations_dataset_id", type_="foreignkey")
