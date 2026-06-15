---
id: CONS-007
title: resolve_provider uses defensive getattr() on ORM columns, hiding schema drift
category: consistency
severity: low
effort: XS
confidence: high
breaking: false
status: open
depends_on: []
blocks: []
supersedes: []
superseded_by: [ARCH-002]
conflicts_with: []
related: []
child_of: ARCH-002
affected_paths:
  - backend/app/services/provider_utils.py
---

## Problem
`resolve_provider` reads ORM attributes via `getattr(db_provider, "field", default)` for eight fields, one of which (`default_params`) does not exist on the `Provider` model at all — so the code silently fabricates `None` instead of failing, masking the model/dataclass drift.

## Evidence
`backend/app/services/provider_utils.py:364-373`; `default_params` at `:367` vs the `Provider` model's columns (`backend/app/models/provider.py:15-34` — no such column).

## Impact
The pattern converts schema drift from a loud AttributeError into silent wrong data. As it happens the whole function is dead code (ARCH-002), so the impact today is zero — this record exists to prevent the pattern from being copied elsewhere.

## Root cause
Written to tolerate databases predating later migrations instead of relying on migrations.

## Proposed fix (specification)
None standalone: ARCH-002 deletes the function. If ARCH-002 were rejected, replace every `getattr(x, "f", d)` with direct attribute access and add the missing column or drop the field.

## Alternatives considered
N/A — symptom record.

## Verification
Covered by ARCH-002 (`grep -rn "getattr(db_provider" backend/` → empty).

## Relationship notes
- `superseded_by: ARCH-002` / `child_of: ARCH-002` — fully removed by that deletion; close together.
