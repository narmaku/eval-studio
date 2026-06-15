---
id: BUG-007
title: POST /providers ignores the single_model field; value flips after the next YAML reload
category: bugs
severity: medium
effort: XS
confidence: high
breaking: false
status: done
depends_on: []
blocks: []
supersedes: []
superseded_by: []
conflicts_with: []
related: [DUP-010]
child_of: null
affected_paths:
  - backend/app/api/v1/providers.py
  - backend/app/core/providers.py
---

## Problem
`ProviderCreate` exposes `single_model` and the FE sends it, but `create_provider` doesn't pass it to the `ProviderProfile` constructor — the in-memory profile gets the dataclass default `False`. Serialization omits `single_model: False`, and on the next file reload `_parse_item` recomputes it from the heuristic `not default_model` — so a provider created with `single_model=true` **and** a default model behaves as `False`, while one created with `single_model=false` and an empty model silently becomes `True` after reload. The value the user chose is never honored, and it changes between "just created" and "after reload".

## Evidence
- Schema field exists: `backend/app/schemas/provider.py:106-112`.
- Constructor call omits it: `backend/app/api/v1/providers.py:204-221` (every other payload field is passed; `single_model` absent).
- Heuristic on reload: `backend/app/core/providers.py:62` (`single_model=raw.get("single_model", not raw.get("default_model", ""))`) and omit-if-False serialization `:87`.
- History: this exact area was patched twice recently (commits `ce2ea6c` "add single-model provider flag", `a311bd5` "auto-detect single_model for YAML providers with empty default_model") — the create path was missed.

## Impact
The "single model" UI toggle is unreliable: value ignored at create time and mutated by the reload heuristic; downstream model-selection UI (which uses the flag to skip model pickers) misbehaves intermittently.

## Root cause
Hand-copied field list in `create_provider` (the disease DUP-010 addresses) missed the newest field.

## Proposed fix (specification)
1. Pass it through: add `single_model=payload.single_model,` in `api/v1/providers.py` create call (after `:218`).
2. Make the persisted value explicit so the reload heuristic can't override a deliberate choice: in `_serialize_item` always emit `single_model` (replace the conditional at `core/providers.py:87` with `"single_model": item.single_model`). The heuristic at `:62` then only applies to hand-written files lacking the key — its intended purpose.

## Alternatives considered
Drop the field and rely purely on the empty-model heuristic — viable simplification, but the schema/UI already shipped the explicit flag; honoring it is the smaller change.

## Verification
Unit/integration: POST provider `{name, default_model:"m", single_model:true}` → GET returns `true`; force `_check_reload` (touch file) → still `true`. Inverse case (`default_model:"", single_model:false`) stays `false` after reload.

## Relationship notes
- `related: DUP-010` — DUP-010's shape collapse removes hand-copied field lists, preventing recurrence; this point fix should land first (user-visible).
