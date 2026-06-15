---
id: BUG-018
title: The evaluator the user selects in the UI is never used — config.evaluator_id is read by nothing
category: bugs
severity: high
effort: S
confidence: high
breaking: false
status: open
depends_on: []
blocks: []
supersedes: []
superseded_by: []
conflicts_with: [SIMP-002]
related: [ARCH-001]
child_of: null
affected_paths:
  - backend/app/services/evaluation_service.py
  - backend/app/services/arena_evaluation_service.py
  - backend/app/services/rag_evaluation_service.py
  - backend/app/adapters/factory.py
  - frontend/src/pages/QAEvaluation.tsx
  - frontend/src/components/evaluation/EvaluatorSelector.tsx
  - frontend/src/stores/evaluatorStore.ts
---

## Problem
Every evaluate page requires the user to pick an evaluator (`isConfigValid` gates on `selectedEvaluatorId`) and sends it as `config.evaluator_id` — but no backend code ever reads that key. All three eval services call `create_evaluation_adapter()` with its default `adapter_type="litellm"`. The entire evaluator-selection feature (selector component, store, API round-trips, config-file management UI) has zero effect on how anything is scored.

## Evidence
- FE sends it and gates on it: `frontend/src/pages/QAEvaluation.tsx:71-73, 85`.
- `grep -rn "evaluator_id" backend/app --include="*.py"` → hits only in `adapters/registry.py` and `api/v1/evaluators.py` (the registry/CRUD themselves); zero hits in any evaluation service.
- Adapter creation with defaults: `services/evaluation_service.py:151-157`, `arena_evaluation_service.py:128-134`, `rag_evaluation_service.py:167-173` — no `adapter_type` argument; factory default `adapter_type="litellm"` (`adapters/factory.py:7-10`).
- Same for agent sessions: `agent_config.evaluator_id` declared in FE types (`frontend/src/types/session.ts:74`) and consumed nowhere.

## Impact
Users are forced through a meaningless required choice; the UI implies pluggable scoring backends that don't exist at runtime. Anyone onboarding a second evaluator via `config/evaluators.yaml` will discover their selection is ignored — the advertised extension point is wired to nothing.

## Root cause
The registry/selector plumbing was built ahead of the dispatch wiring, and with only one evaluator nobody noticed the missing last mile.

## Proposed fix (specification)
Two coherent end-states; this issue specifies the **wire-it** option (the delete option is SIMP-002 — they conflict, see notes):
1. In each eval service (or the post-ARCH-001 runner), replace `create_evaluation_adapter(model=…)` with `create_evaluation_adapter(config.get("evaluator_id", "litellm"), model=…)`.
2. On `ValueError` from the factory (unknown/unavailable evaluator), fail the evaluation early with `error="Evaluator '<id>' is not available"` (reuses the existing fail path).
3. Validate at create time too: in `create_evaluation`/`run_and_wait`, if `config.evaluator_id` is present and not in `evaluator_registry`, raise `ValidationException` (fast feedback).

## Alternatives considered
Delete the selector + registry (SIMP-002) — equally coherent and more aligned with the simplicity goal; requires product judgment on whether external evaluator onboarding (lightspeed-evaluation per README) is near-term. ROADMAP must pick exactly one.

## Verification
Unit: eval config with `evaluator_id: "litellm-judge"` constructs via registry (spy on `evaluator_registry.create_adapter`); unknown id → evaluation fails fast with the clear error. FE flow unchanged.

## Relationship notes
- `conflicts_with: SIMP-002` — SIMP-002 deletes the machinery this issue wires up; mutually exclusive end-states for the same code. ROADMAP records the recommendation (SIMP-002 unless lightspeed-evaluation integration is scheduled).
- `related: ARCH-001` — whichever option wins should be implemented in the consolidated runner, not three times.
