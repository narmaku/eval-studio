"""Drift detection: the checked-in WS protocol snapshot must match the Pydantic models.

If this test fails, the backend envelope schema changed without regenerating
the snapshot. Fix by running:
    cd backend && uv run python scripts/gen_ws_schema.py
"""

import json
from pathlib import Path

from app.schemas.ws_chat import (
    ConnectedMsg,
    ErrorMsg,
    MessageChunk,
    MessageComplete,
    SessionEndedMsg,
    ToolCallMsg,
    ToolExecutingMsg,
    ToolResultMsg,
)

ENVELOPE_TYPES = [
    ConnectedMsg,
    MessageChunk,
    MessageComplete,
    ToolCallMsg,
    ToolExecutingMsg,
    ToolResultMsg,
    SessionEndedMsg,
    ErrorMsg,
]

SNAPSHOT_PATH = Path(__file__).resolve().parents[3] / "frontend" / "src" / "types" / "generated" / "ws_protocol.json"


def test_ws_protocol_snapshot_up_to_date():
    assert SNAPSHOT_PATH.exists(), (
        f"WS protocol snapshot missing at {SNAPSHOT_PATH}. Run: cd backend && uv run python scripts/gen_ws_schema.py"
    )

    current = {cls.__name__: cls.model_json_schema() for cls in ENVELOPE_TYPES}
    snapshot = json.loads(SNAPSHOT_PATH.read_text())

    assert current == snapshot, (
        "WS protocol snapshot is out of date. Run: cd backend && uv run python scripts/gen_ws_schema.py"
    )


def test_all_envelope_types_have_type_field():
    """Every envelope has a 'type' literal field so messages are discriminable."""
    for cls in ENVELOPE_TYPES:
        schema = cls.model_json_schema()
        props = schema.get("properties", {})
        assert "type" in props, f"{cls.__name__} is missing a 'type' property"
        type_prop = props["type"]
        assert "const" in type_prop, f"{cls.__name__}.type is not a Literal const"


def test_all_envelope_types_share_base_fields():
    """Every envelope inherits timestamp, sender, session_id from _Envelope."""
    for cls in ENVELOPE_TYPES:
        schema = cls.model_json_schema()
        props = schema.get("properties", {})
        for field in ("timestamp", "sender", "session_id"):
            assert field in props, f"{cls.__name__} is missing base field '{field}'"
