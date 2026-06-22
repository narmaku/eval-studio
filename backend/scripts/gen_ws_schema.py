#!/usr/bin/env python3
"""Generate the WebSocket protocol JSON-schema snapshot.

Outputs to frontend/src/types/generated/ws_protocol.json so both
the backend drift-detection test and the frontend conformance test
can reference a single checked-in source of truth.

Usage:
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

SNAPSHOT_PATH = Path(__file__).resolve().parents[2] / "frontend" / "src" / "types" / "generated" / "ws_protocol.json"


def generate() -> dict:
    return {cls.__name__: cls.model_json_schema() for cls in ENVELOPE_TYPES}


if __name__ == "__main__":
    schema = generate()
    SNAPSHOT_PATH.parent.mkdir(parents=True, exist_ok=True)
    SNAPSHOT_PATH.write_text(json.dumps(schema, indent=2) + "\n")
    print(f"Wrote {SNAPSHOT_PATH}")
