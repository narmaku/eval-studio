"""datetime_timezone_aware

Switch all DateTime columns to DateTime(timezone=True).  SQLite stores
ISO strings with offset when aware datetimes are written; existing rows
that were stored naive-UTC gain no offset (treated as UTC by convention).

Revision ID: 2c32845ca520
Revises: 9d2fc61ed930
Create Date: 2026-06-22

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "2c32845ca520"
down_revision: str | None = "9d2fc61ed930"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

TABLES_AND_COLUMNS = [
    ("evaluations", ["created_at", "updated_at"]),
    ("judge_configs", ["created_at", "updated_at"]),
    ("datasets", ["created_at", "updated_at"]),
    ("dataset_items", ["created_at"]),
    ("results", ["created_at"]),
    ("sessions", ["created_at", "started_at", "ended_at"]),
    ("artifacts", ["created_at"]),
    ("rubrics", ["created_at", "updated_at"]),
    ("api_keys", ["created_at", "last_used_at"]),
]


def upgrade() -> None:
    for table, columns in TABLES_AND_COLUMNS:
        with op.batch_alter_table(table) as batch_op:
            for col in columns:
                batch_op.alter_column(
                    col,
                    existing_type=sa.DateTime(),
                    type_=sa.DateTime(timezone=True),
                )


def downgrade() -> None:
    for table, columns in TABLES_AND_COLUMNS:
        with op.batch_alter_table(table) as batch_op:
            for col in columns:
                batch_op.alter_column(
                    col,
                    existing_type=sa.DateTime(timezone=True),
                    type_=sa.DateTime(),
                )
