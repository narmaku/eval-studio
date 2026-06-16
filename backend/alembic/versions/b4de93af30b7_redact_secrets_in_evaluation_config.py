"""redact_secrets_in_evaluation_config

Data migration: scrub secret-bearing keys from the ``evaluations.config``
JSON column in existing rows.  Keys matching auth/token/key/secret/password/
connection_string patterns are set to ``"**REDACTED**"``.

Revision ID: b4de93af30b7
Revises: f25d781af937
Create Date: 2026-06-16 12:28:01.832346

"""

import json
import re
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "b4de93af30b7"
down_revision: str | None = "f25d781af937"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_SECRET_RE = re.compile(r"(auth|token|key|secret|password|connection_string)", re.IGNORECASE)
_REDACTED = "**REDACTED**"


def _redact(obj: dict) -> dict:
    out: dict = {}
    for k, v in obj.items():
        if v is None:
            out[k] = None
        elif _SECRET_RE.search(k):
            out[k] = _REDACTED
        elif isinstance(v, dict):
            out[k] = _redact(v)
        else:
            out[k] = v
    return out


def upgrade() -> None:
    conn = op.get_bind()
    rows = conn.execute(sa.text("SELECT id, config FROM evaluations WHERE config IS NOT NULL")).fetchall()
    for row_id, raw_config in rows:
        try:
            config = json.loads(raw_config) if isinstance(raw_config, str) else raw_config
        except (json.JSONDecodeError, TypeError):
            continue
        if not isinstance(config, dict):
            continue
        redacted = _redact(config)
        if redacted != config:
            conn.execute(
                sa.text("UPDATE evaluations SET config = :config WHERE id = :id"),
                {"config": json.dumps(redacted), "id": row_id},
            )


def downgrade() -> None:
    pass
