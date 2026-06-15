---
id: BUG-012
title: RAG metric pass flags use a hardcoded 0.7 threshold and temperature, ignoring judge config
category: bugs
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
related: [DUP-006, ARCH-001]
child_of: null
affected_paths:
  - backend/app/adapters/litellm_judge.py
  - backend/app/adapters/base.py
  - backend/app/services/rag_evaluation_service.py
---

## Problem
`evaluate_rag` is the only judge method that doesn't receive `JudgeConfigParams`: per-metric `passed` flags use a literal `threshold = 0.7` and the call uses `temperature: 0.0` unconditionally. Meanwhile the RAG service computes the *overall* verdict with the configured `judge_params.pass_threshold` — so with a configured threshold of 0.5, a metric scoring 0.6 is simultaneously "failed" (per-metric) and contributes to a "passed" overall.

## Evidence
- Hardcoded: `backend/app/adapters/litellm_judge.py:319` (`threshold = 0.7`), `:349` (`"temperature": 0.0`); signature without judge_config `:309-316` mirrors the ABC `adapters/base.py:96-104`.
- Configured path for overall: `services/rag_evaluation_service.py:229-230` (`threshold = judge_params.pass_threshold or 0.7`).
- Contrast: `evaluate_qa` honors config (`litellm_judge.py:175,202`), `evaluate_conversation` too (`:274,305`).

## Impact
Inconsistent pass/fail displays in the RAG results UI whenever a non-default threshold is configured; judge temperature config silently ignored for RAG.

## Root cause
`evaluate_rag` was added with a narrower signature and never aligned.

## Proposed fix (specification)
1. Add `judge_config: JudgeConfigParams` to `evaluate_rag` in the ABC (`adapters/base.py:96-104`) and implementation; use `judge_config.pass_threshold or 0.7` for per-metric flags and `judge_config.temperature` for the call.
2. Update the single call site `rag_evaluation_service.py:218-224` to pass `judge_params`.
3. If DUP-006 lands first, this collapses into passing judge_config through `_ask_judge`.

## Alternatives considered
Drop per-metric `passed` flags entirely (report scores only) — defensible, but the FE renders them; keep and fix.

## Verification
`tests/unit/test_rag_judge.py`: configure `pass_threshold=0.5`, mock judge returning 0.6 → all four metric Scores have `passed=True`.

## Relationship notes
- `related: DUP-006` — same file/method; cheapest implemented together.
- `related: ARCH-001` — caller moves into `RAGRunner`; no ordering constraint.
