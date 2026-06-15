---
id: API-005
title: /judges/presets returns provider profiles disguised as judge configs with synthetic ids
category: api-contracts
severity: low
effort: S
confidence: high
breaking: true
status: open
depends_on: []
blocks: []
supersedes: []
superseded_by: []
conflicts_with: []
related: [DATA-005]
child_of: null
affected_paths:
  - backend/app/api/v1/judges.py
  - frontend/src/components/evaluation/JudgeConfigPanel.tsx
  - frontend/src/services/api.ts
---

## Problem
`GET /judges/presets` fabricates `JudgeConfigResponse` objects from provider profiles "for backward compat": ids are `provider-{uuid}` strings that resolve to no judge resource (GET /judges/{id} would 404), timestamps are `now()` at request time, and every judge field except `model` is a hardcoded default. A "preset" is thus neither a judge nor stable.

## Evidence
`backend/app/api/v1/judges.py:75-101` — docstring admits it ("Returns all provider profiles as JudgeConfigResponse for backward compat"); synthetic id at `:88`, `created_at=now` `:84,97-98`.

## Impact
The FE judge panel consumes a shape that lies about its identity; selecting a "preset" can't round-trip through any judge endpoint; the `provider-` prefix is implicit string protocol between BE and FE.

## Root cause
The judge-selection UI was repointed at providers (any provider can judge) without changing the response contract — the masquerade preserved the old FE shape.

## Proposed fix (specification)
1. DELETE the `/judges/presets` endpoint.
2. FE `JudgeConfigPanel` selects a judge **provider** directly via the existing `listProviders()` (it already has the data; the panel's value is `{provider_id}` — which is exactly what the backend judge resolution consumes, `provider_utils.py:158-162`); remove `listJudgePresets` from `api.ts:197` and the `JudgePreset` type.
3. If named judge presets (model+prompt+threshold bundles) are wanted as a feature, that's the Rubric/JudgeConfig consolidation's job (DATA-005), not a fabricated view.

## Alternatives considered
Return providers under an honest schema (`JudgePresetResponse{provider_id, name, model}`) — acceptable fallback if the FE panel must keep a dedicated endpoint; still removes the fake ids.

## Verification
FE judge selection flow works against providers; `grep -rn "presets" backend/app frontend/src` → nothing; eval creation payloads unchanged (`judge_config.provider_id`).

## Relationship notes
- `related: DATA-005` — the judge/rubric model consolidation defines where real presets would live; no hard ordering (this deletion stands alone).
