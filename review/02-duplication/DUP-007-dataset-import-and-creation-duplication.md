---
id: DUP-007
title: Dataset+items persistence and DatasetDetailResponse assembly written four times
category: duplication
severity: medium
effort: S
confidence: high
breaking: false
status: open
depends_on: []
blocks: []
supersedes: []
superseded_by: []
conflicts_with: []
related: [DUP-011]
child_of: null
affected_paths:
  - backend/app/api/v1/dataset_import.py
  - backend/app/api/v1/datasets.py
---

## Problem
Creating a Dataset row, looping items into `DatasetItem` rows, committing, and hand-assembling a `DatasetDetailResponse` (including per-item `DatasetItemResponse` mapping) is implemented once in `datasets.create_dataset` and twice more inside `import_dataset`'s "single" and "separate" branches — the two import branches are ~90 lines of near-identical code differing only in naming and looping.

## Evidence
- `backend/app/api/v1/datasets.py:26-80` (create_dataset).
- `backend/app/api/v1/dataset_import.py:183-250` (merge_mode == "single") vs `:252-323` (separate) — same Dataset construction (`:196-204` vs `:267-275`), same item loop (`:208-218` vs `:279-289`), same response assembly (`:226-250` vs `:294-319`).
- `DatasetItemResponse` hand-mapping additionally at `datasets.py:56-65` and `:122-131`.

## Impact
Four places to update for any dataset field addition; the import branches have already required parallel edits (both construct `format="qa_pairs"`, `source_type="import"`).

## Root cause
"Separate mode" written by copying "single mode"; import endpoint written by copying create_dataset.

## Proposed fix (specification)
1. Add to a new `backend/app/services/dataset_service.py`:
   ```python
   async def create_dataset_with_items(db, *, name, description, version, tags,
                                       source_type, items: list[dict]) -> Dataset
   def to_detail_response(dataset: Dataset, items: list[DatasetItem]) -> DatasetDetailResponse
   ```
2. `create_dataset` and both import branches call these; the import endpoint's two branches reduce to: build `(name, rows)` pairs (one pair for "single", one per file for "separate") then loop a single code path.
3. Net deletion ≈ 110 lines.

## Alternatives considered
`from_attributes` model_validate for the detail response — works only if relationship access patterns are consistent; the explicit builder is clearer given `metadata_` aliasing.

## Verification
`uv run pytest tests/integration/test_dataset_import_api.py tests/unit/test_dataset_import_service.py` green; both merge modes still return identical JSON (snapshot one response per mode before refactor).

## Relationship notes
- `related: DUP-011` — sibling duplication in the same feature (schema extraction); independent fixes.
