---
id: DATA-002
title: Dataset.tags annotated as dict but defaulted and used as list
category: data-model
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
related: []
child_of: null
affected_paths:
  - backend/app/models/dataset.py
---

## Problem
`Dataset.tags` is typed `Mapped[dict | None]` with `default=list` — the annotation says dict, the default produces a list, and all real data is a list of strings (schemas declare `tags: list[str]`).

## Evidence
- `backend/app/models/dataset.py:20`: `tags: Mapped[dict | None] = mapped_column(JSON, nullable=True, default=list)`.
- Actual shape: `schemas/dataset.py` (`tags` as `list[str]` in create/response — see `DatasetCreate` usage `api/v1/datasets.py:34`); sibling done right: `models/provider.py:25` (`Mapped[list]`).

## Impact
Type checkers and readers get the wrong contract; a JSON column hides it at runtime, which is exactly why it should be fixed before something trusts the annotation.

## Root cause
Copy-edit slip.

## Proposed fix (specification)
`tags: Mapped[list | None] = mapped_column(JSON, nullable=True, default=list)` — one-line change; no migration (JSON storage unchanged).

## Alternatives considered
None needed.

## Verification
`uv run pytest tests/integration/test_dataset_import_api.py` green; if mypy/pyright is ever enabled, no new error here.

## Relationship notes
None — quick win.
