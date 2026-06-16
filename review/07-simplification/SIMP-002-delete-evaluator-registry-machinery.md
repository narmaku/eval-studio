---
id: SIMP-002
title: Delete the evaluator registry/factory machinery and selector UI (one adapter, zero dispatch)
category: simplification
severity: high
effort: M
confidence: high
breaking: true
status: open (permanently rejected)
depends_on: []
blocks: [TEST-002]
supersedes: [SIMP-005]
superseded_by: []
conflicts_with: [BUG-018]
related: [ARCH-001, DOC-001]
child_of: null
affected_paths:
  - backend/app/adapters/registry.py
  - backend/app/adapters/factory.py
  - backend/app/api/v1/evaluators.py
  - config/evaluators.yaml
  - frontend/src/components/evaluation/EvaluatorSelector.tsx
  - frontend/src/components/settings/EvaluatorList.tsx
  - frontend/src/components/settings/EvaluatorDetail.tsx
  - frontend/src/stores/evaluatorStore.ts
  - frontend/src/types/evaluator.ts
---

## Problem
The pluggable-evaluator system — YAML registry with dynamic import and namespace allowlisting, factory, discovery API, config-file upload API, FE selector on every evaluate page, settings UI, and store — exists to choose among evaluation adapters. There is exactly one adapter, and (BUG-018) the chosen id is never even consulted at runtime. This is speculative generality at its purest: ~1,200 lines across both tiers whose entire runtime effect is `return LiteLLMJudgeAdapter(**kwargs)`.

## Evidence
- One adapter registered: `config/evaluators.yaml` (single entry); one implementation: `grep -rln "EvaluationAdapter)" backend/app/adapters` → `litellm_judge.py` only.
- Factory always called with default: `services/evaluation_service.py:151`, `arena_evaluation_service.py:128`, `rag_evaluation_service.py:167` (no `adapter_type` arg → `"litellm"` branch, `adapters/factory.py:29-32`).
- Machinery: `adapters/registry.py` (180 lines incl. importlib + namespace validation), `api/v1/evaluators.py` (211 lines incl. config-file upload subsystem whose files nothing reads back at runtime: `grep -rn "evaluator_config_dir" backend/app` → only config.py and evaluators.py).
- FE: `EvaluatorSelector` gates every evaluate page (`pages/QAEvaluation.tsx:71-73`), plus `EvaluatorList/Detail`, `evaluatorStore`, `types/evaluator.ts`.
- Selected value ignored: BUG-018 evidence.

## Impact
Users make a meaningless required choice; contributors maintain dynamic-import security machinery (namespace allowlists, availability probing) protecting a dispatch that never happens; the unused config-file upload endpoints are attack/maintenance surface.

## Root cause
Architecture built ahead of the second integration (lightspeed-evaluation per README) that hasn't arrived.

## Proposed fix (specification)
Deletion list:
1. DELETE `backend/app/adapters/registry.py`, `adapters/factory.py`; the three service call sites construct `LiteLLMJudgeAdapter(...)` directly (or the single post-ARCH-001 runner does, once).
2. DELETE `backend/app/api/v1/evaluators.py` (router include `main.py:138,156`), `config/evaluators.yaml`, `evaluator_config_dir` setting (`core/config.py:32`), and `EVALUATOR_CONFIG_DIR`/`EVALUATORS_CONFIG_PATH` lines in `.env.example`.
3. DELETE FE: `EvaluatorSelector.tsx(+test)`, `EvaluatorList/Detail(+tests)`, `evaluatorStore(+test)`, `types/evaluator.ts`, the two `api.ts` evaluator sections (`:265-314`), selector usage + `selectedEvaluatorId` gating on the four evaluate pages, evaluator tab in `pages/Settings.tsx`.
4. DELETE backend tests: `test_evaluator_registry.py`, `test_eval_adapter_factory.py`, `test_evaluator_config_files.py`; FE tests of deleted components.
5. Keep `adapters/base.py` (Score/JudgeConfigParams/ABC trimmed per SIMP-005's analysis — fold that trim into this change) and `litellm_judge.py`.
Estimated deletion ≈ 1,400 lines (backend ~700, frontend ~700).
Re-introduction path (recorded for the future): when a second scoring backend really lands, reintroduce a `dict[str, type]` factory — a registry earns its complexity at N≥2, not before.

## Alternatives considered
Wire the selection instead (BUG-018's spec) — coherent if lightspeed-evaluation integration is genuinely scheduled. The repo shows no in-progress work toward it (no adapter, no branch artifacts), so this issue recommends deletion. ROADMAP makes the final call; exactly one of SIMP-002/BUG-018 may be implemented.

## Verification
- `uv run pytest` and `npm test -- --run` green post-deletion; `tsc --noEmit` clean.
- Evaluate pages no longer require an evaluator choice; QA/RAG/arena flows run end-to-end.
- `grep -rn "evaluator" backend/app frontend/src -il` → only litellm_judge internals and historical migrations.

## Relationship notes
- `conflicts_with: BUG-018` — mutually exclusive resolutions of the same defect ("selection does nothing"): delete the choice vs honor it. Recommendation: this issue wins absent a concrete second-evaluator commitment.
- `supersedes: SIMP-005` — the ABC-surface trim is subsumed by step 5 here.
- `related: ARCH-001` — adapter construction site count drops to one there; either order works (ARCH-001 first makes step 1 a one-line edit).
- `related: DOC-001` — CLAUDE.md "Adding a New Evaluation Adapter" workflow must be rewritten/removed accordingly.
