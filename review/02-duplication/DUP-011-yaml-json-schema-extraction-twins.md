---
id: DUP-011
title: _extract_yaml_schema and _extract_json_schema are structural twins
category: duplication
severity: low
effort: XS
confidence: high
breaking: false
status: open
depends_on: []
blocks: []
supersedes: []
superseded_by: []
conflicts_with: []
related: [DUP-007]
child_of: null
affected_paths:
  - backend/app/services/dataset_import_service.py
---

## Problem
The YAML and JSON schema extractors are the same function after the parse call: both take "parsed is list / dict-with-first-list-key / scalar" and build identical row lists and FileSchema results.

## Evidence
`backend/app/services/dataset_import_service.py:277-305` (`_extract_yaml_schema`) vs `:335-362` (`_extract_json_schema`) — bodies differ only in `yaml.safe_load` vs `json.loads` and one comment.

## Impact
~30 duplicated lines; the "first list-valued key" heuristic must be fixed in two places if it changes.

## Root cause
JSON extractor copied from the YAML one.

## Proposed fix (specification)
1. `def _rows_from_parsed(parsed: Any) -> list[dict]` holding the shared branch logic.
2. Both extractors become `parse → _rows_from_parsed → _build_schema(rows, sample_size)` (the FileSchema assembly at `:297-305`/`:354-362` is also identical and joins the helper).
3. Net deletion ≈ 35 lines.

## Alternatives considered
Do nothing — acceptable; filed because the import service is an active edit area (DUP-007).

## Verification
`uv run pytest tests/unit/test_dataset_import_service.py` green.

## Relationship notes
- `related: DUP-007` — same feature area; both are independent of each other.
