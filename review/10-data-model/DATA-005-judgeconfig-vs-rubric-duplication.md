---
id: DATA-005
title: JudgeConfig and Rubric are two tables for one concept (scoring criteria)
category: data-model
severity: medium
effort: L
confidence: medium
breaking: true
status: open
depends_on: []
blocks: []
supersedes: []
superseded_by: []
conflicts_with: []
related: [API-005, ARCH-001, DATA-006]
child_of: null
affected_paths:
  - backend/app/models/evaluation.py
  - backend/app/models/rubric.py
  - backend/app/api/v1/judges.py
  - backend/app/api/v1/rubrics.py
  - frontend/src/components/settings/RubricList.tsx
  - frontend/src/components/evaluation/JudgeConfigPanel.tsx
---

## Problem
`JudgeConfig` (judge_configs table) and `Rubric` (rubrics table) carry the same payload — `dimensions` JSON, `pass_threshold`, `aggregation`, `prompt_template`, name/description — split across two models, two routers, two FE settings areas. JudgeConfig adds `model`/`temperature`/`preset` (judge *runtime* parameters); Rubric is the newer, richer concept with AI generate/refine. Meanwhile the actual runtime mostly ignores both: QA scoring reads only `prompt_template`/threshold/temperature (the `dimensions` field is consulted by no scoring path — `evaluate_qa` never touches `judge_config.dimensions`), and judge model selection has moved to providers (API-005).

## Evidence
- Field overlap: `backend/app/models/evaluation.py:35-46` vs `models/rubric.py:15-24` (dimensions/pass_threshold/aggregation/prompt_template in both).
- `dimensions` unused in scoring: `adapters/litellm_judge.py:157-203` (`evaluate_qa` uses prompt_template/threshold/temperature only); conversation/RAG use **hardcoded** dimension sets (`:94, :67`).
- Two CRUD routers: `api/v1/judges.py` (no DELETE — `grep -n "delete" api/v1/judges.py` → none), `api/v1/rubrics.py` (full CRUD + import/generate/refine).
- Rubrics are not connectable to evaluations at all: `grep -rn "rubric" backend/app/services backend/app/api/v1/evaluations.py` → nothing — the entire Rubric feature (build/generate/refine UI included) produces rows that no evaluation can reference.

## Impact
Two halves of one feature, each incomplete: judges are wired to evaluations but can't be built with the rubric tools; rubrics have the design tools but can't be used in evaluations. Users can author rubrics that do nothing — a feature-shaped dead end mirroring BUG-018.

## Root cause
Rubric (with rubric-kit) was added as a new vertical instead of evolving JudgeConfig; integration last-mile never happened.

## Proposed fix (specification)
Consolidate on **Rubric** as the criteria object and reduce JudgeConfig to its runtime essence:
1. Add `rubric_id: str | None = ForeignKey("rubrics.id")` to evaluations' judge reference path: extend `resolve_judge_config`/`to_judge_params` so `config.judge_config = {provider_id, rubric_id, pass_threshold?}` loads the rubric's prompt_template/dimensions/threshold into `JudgeConfigParams` (`services/judge_utils.py`).
2. Wire `dimensions` into scoring or drop the field's pretense: minimal honest version — when a rubric supplies `dimensions`, build the QA prompt from them (template section listing name/description/weight, response schema `{"<dim>": float, ..., "reasoning"}`), aggregate by weights into `Score.breakdown`/`value`. This makes the rubric builder real. (~80 lines in `litellm_judge.py`, lands cleanly inside DUP-006's `_ask_judge` refactor.)
3. DEPRECATE-and-DELETE the `judge_configs` table + `/api/v1/judges` router + FE judge CRUD (the panel keeps provider + rubric pickers; API-005 already removes presets). Migration: convert existing judge_configs rows with custom prompt_templates into rubrics; drop table (fold into DATA-006).
4. FE: `JudgeConfigPanel` = provider select + optional rubric select + threshold; Settings keeps only the Rubrics tab.

## Alternatives considered
1. Consolidate on JudgeConfig and delete Rubric — rejected: loses the generate/refine integration (rubric-kit) which is a headline feature.
2. Keep both, add rubric→judge import — rejected: preserves two stores for one concept.

## Verification
- E2E: build a rubric (or generate), select it in a QA eval, run → `scores_breakdown` keyed by the rubric's dimensions; weights respected (unit test on the aggregation).
- `GET /api/v1/judges` gone; migration converts a seeded judge_config row to a rubric.

## Relationship notes
- `related: API-005` — presets removal is a precondition for shrinking the judge panel; either order technically works.
- `related: ARCH-001` — judge param threading happens in the consolidated runner; do ARCH-001 first to implement step 1 once.
- `related: DATA-006` — table drop joins the migration cleanup.
- `confidence: medium` reflects product judgment (which concept wins), not the factual findings, which are high-confidence.
