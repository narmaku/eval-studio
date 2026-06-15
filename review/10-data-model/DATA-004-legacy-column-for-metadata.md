---
id: DATA-004
title: DatasetItem.metadata_ uses legacy Column() instead of mapped_column
category: data-model
severity: trivial
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
The single 1.x-style `Column()` declaration in an otherwise uniformly 2.0-style codebase, used for the `metadata` name aliasing.

## Evidence
`backend/app/models/dataset.py:36`: `metadata_: Mapped[dict | None] = Column("metadata", JSON, nullable=True)` — every other column in the repo uses `mapped_column`.

## Impact
Style inconsistency only; the aliasing works either way.

## Root cause
Probably uncertainty about aliasing syntax under `mapped_column` (the `metadata` attribute name is reserved by SQLAlchemy's Declarative).

## Proposed fix (specification)
`metadata_: Mapped[dict | None] = mapped_column("metadata", JSON, nullable=True)` — `mapped_column` accepts the positional column name identically. No migration.

## Alternatives considered
None needed.

## Verification
`uv run pytest tests/integration/test_dataset_import_api.py` green; emitted DDL/queries still use the `metadata` column name.

## Relationship notes
None — quick win.
