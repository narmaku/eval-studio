---
id: DUP-010
title: The provider shape is declared four times (dataclass, ORM, Pydantic schemas, ResolvedModel)
category: duplication
severity: medium
effort: M
confidence: high
breaking: false
status: open
depends_on: [ARCH-002]
blocks: []
supersedes: []
superseded_by: []
conflicts_with: []
related: [ARCH-004, DUP-009, BUG-007]
child_of: null
affected_paths:
  - backend/app/core/providers.py
  - backend/app/models/provider.py
  - backend/app/schemas/provider.py
  - backend/app/services/provider_utils.py
  - backend/app/api/v1/providers.py
---

## Problem
A provider's ~16 fields are declared in four parallel shapes: `ProviderProfile` dataclass, the dead `Provider` ORM model, three Pydantic schemas (`ProviderCreate`/`Update`/`Response`), and `ResolvedModel` (which restates 12 of the fields). Field-by-field copying between them is manual (`_provider_to_response`, `_parse_item`/`_serialize_item`, `resolve_model_config`'s 15-assignment block) — which is exactly where BUG-007 (dropped `single_model`) was born.

## Evidence
- `backend/app/core/providers.py:11-38` (dataclass) and `:46-90` (parse/serialize mirrors).
- `backend/app/models/provider.py:15-34` (ORM, dead — ARCH-002).
- `backend/app/schemas/provider.py:19-167` (Create/Update/Response).
- `backend/app/services/provider_utils.py:21-37` (ResolvedModel) and the copying block `:84-121`.
- Manual mapper `api/v1/providers.py:60-80`.

## Impact
Adding one provider field today requires touching 6–7 locations; misses are silent (BUG-007 is the live example).

## Root cause
Layer-per-shape orthodoxy applied to a config object that has no behavioral divergence between layers.

## Proposed fix (specification)
After ARCH-002 removes the ORM copy:
1. Make the Pydantic model the single source: replace the `ProviderProfile` dataclass with a Pydantic `ProviderProfile(BaseModel)` in `core/providers.py`; `_parse_item` → `ProviderProfile.model_validate(raw)` (with a `model_config = ConfigDict(extra="ignore")`), `_serialize_item` → `item.model_dump(exclude_defaults=True)` (preserves the current omit-defaults YAML style; verify `response_json_path` default round-trips).
2. `ProviderCreate` becomes `ProviderProfile` minus `id` (inherit or `model_construct`); `ProviderResponse` = `ProviderProfile` minus `api_key_env` plus `has_api_key` (keep the never-expose-key rule, `schemas/provider.py:147-148`); DELETE `_provider_to_response`'s 16-field copy in favor of `ProviderResponse.model_validate(profile, from_attributes=True)` + computed `has_api_key`.
3. Shrink `ResolvedModel`: replace its 12 copied fields with `provider: ProviderProfile | None` + the 3 resolution outputs that differ (`model`, `api_key`, `api_base`); update the ~6 consumers (`call_model`, adapters factory, evaluation services).
4. Net deletion ≈ 150 lines; new fields then require exactly one declaration.

## Alternatives considered
Keep dataclass + schemas but generate mappers — rejected: mapper generation is more machinery than collapsing the shapes.

## Verification
`uv run pytest tests/unit/test_providers.py tests/unit/test_provider_schemas.py tests/integration/test_providers_api.py tests/unit/test_provider_utils.py` green; round-trip test: create provider via API → reload registry from YAML → fields identical (catches serialize/parse asymmetry, incl. BUG-007's field).

## Relationship notes
- `depends_on: ARCH-002` — collapsing shapes while the dead ORM copy exists would mean migrating to it or around it; delete it first.
- `related: BUG-007` — fixed automatically by step 2 (no hand-copied field list); a point-fix may land earlier.
- `related: ARCH-004` — once the Pydantic shape is canonical, the FE Provider type comes from codegen.
- `related: DUP-009` — same files; do this one second.
