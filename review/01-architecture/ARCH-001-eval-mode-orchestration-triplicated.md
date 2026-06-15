---
id: ARCH-001
title: Q&A/Arena/RAG evaluation services are three copies of one orchestration skeleton
category: architecture
severity: high
effort: L
confidence: high
breaking: false
status: open
depends_on: []
blocks: [TEST-003]
supersedes: [DUP-003, DUP-004]
superseded_by: []
conflicts_with: []
related: [BUG-001, BUG-010, BUG-015, DUP-006, ARCH-007]
child_of: null
affected_paths:
  - backend/app/services/evaluation_service.py
  - backend/app/services/arena_evaluation_service.py
  - backend/app/services/rag_evaluation_service.py
  - backend/app/services/run_service.py
  - backend/app/api/v1/evaluations.py
---

## Problem
The three batch evaluation modes are implemented as three nearly identical ~330-line functions. Every lifecycle concern — loading the evaluation, status transitions, dataset/judge loading, judge resolution, semaphore fan-out, result collection, failure accounting, artifact generation, and the outer crash handler — is copy-pasted three times. Mode dispatch (`if mode == "arena" … elif "rag" … else qa`) is additionally duplicated in four call sites.

## Evidence
- `backend/app/services/evaluation_service.py:28-322` (`run_qa_evaluation`), `arena_evaluation_service.py:30-358` (`run_arena_evaluation`), `rag_evaluation_service.py:65-347` (`run_rag_evaluation`).
- Steps 1–4 are line-for-line identical, e.g. dataset loading: `evaluation_service.py:46-62` vs `arena_evaluation_service.py:48-64` vs `rag_evaluation_service.py:83-99`.
- Identical outer exception handler in all three: `evaluation_service.py:311-322`, `arena_evaluation_service.py:347-358`, `rag_evaluation_service.py:336-347`.
- Result-collection loop identical between qa and rag: `evaluation_service.py:262-290` vs `rag_evaluation_service.py:287-315`.
- Mode dispatch duplicated ×4: `api/v1/evaluations.py:200-205`, `:319-324`, `:364-369`; `services/run_service.py:47-52`.
- Failed-status boilerplate (`status="failed"; error=…; commit; broadcast_status`) appears 12 times across the three files (e.g. `evaluation_service.py:48-52,58-62,75-79,98-102,129-133`).

## Impact
~700 of ~1,030 lines are duplicated. Every lifecycle fix must be applied three times and routinely isn't: the RAG mode honors `judge_params.pass_threshold` for the overall verdict while QA/Arena differ on per-metric thresholds (BUG-012), error-result construction drifted (`contestant_model` only in arena), and the dead `except ValueError` around model resolution (BUG-001) exists in two of the three. Adding a future mode means a fourth copy.

## Root cause
Arena and RAG were created by copying the Q&A service and editing the middle (`rag_evaluation_service.py:5` even says "Refactored from inline httpx code" for only the adapter part). No shared runner was ever extracted.

## Proposed fix (specification)
Collapse to one orchestrator plus per-mode item runners.

1. Create `backend/app/services/eval_runner.py`:
   ```python
   class ItemOutcome:  # dataclass: score fields + actual_answer + chunks + contestant
   class ModeRunner(Protocol):
       async def prepare(self, evaluation, config) -> None: ...   # mode-specific validation/resolution
       def tasks(self, items) -> Iterable[TaskSpec]: ...          # item (× contestant for arena)
       async def run_item(self, spec) -> ItemOutcome: ...

   async def run_evaluation(evaluation_id: str, db: AsyncSession) -> None:
       # single copy of: load+guard status, load dataset, load judge config,
       # resolve judge, build judge adapter, semaphore fan-out over runner.tasks(),
       # collect results (one Result-builder), final status, broadcast, artifacts,
       # outer crash handler
   ```
2. Implement three small runners (~40–80 lines each): `QARunner` (call_model + evaluate_qa), `ArenaRunner` (adds contestants resolution; `prepare` enforces ≥2 resolvable contestants), `RAGRunner` (rag adapter + evaluate_rag + chunk mapping; closes the adapter in `finally` — fixes BUG-009 as a side effect).
3. Introduce a single helper `async def fail(evaluation, db, detail: str)` used for every early-exit (replaces the 12 copies).
4. Replace the four dispatch sites with one `MODE_RUNNERS: dict[str, type[ModeRunner]]` lookup in `eval_runner.py`; `api/v1/evaluations.py` and `run_service.py` call only `run_evaluation(...)`.
5. DELETE `arena_evaluation_service.py` and `rag_evaluation_service.py` as separate skeletons (keep mode-specific logic in their runner classes; net deletion ≈ 600 lines).
6. Keep WS broadcast call points identical (same message strings) so the FE log panel behavior is unchanged.

## Alternatives considered
1. Shared helper functions but three top-level services kept — rejected: leaves triple dispatch and triple crash handlers, the costliest parts.
2. Full strategy-pattern "EvaluationMode" plugin registry — rejected: over-engineering; three known modes, a dict is enough.

## Verification
- `uv run pytest tests/unit/test_evaluation_service.py tests/unit/test_arena_evaluation_service.py tests/unit/test_rag_evaluation_service.py tests/integration/test_qa_flow.py tests/integration/test_arena_api.py` — port assertions to the new runner module.
- Add one parametrized lifecycle test (pending→running→completed/failed, all-items-fail ⇒ failed) executed for all three modes — only possible post-consolidation.
- `grep -rn "run_arena_evaluation\|run_rag_evaluation" backend/` returns nothing.

## Relationship notes
- `supersedes: DUP-003, DUP-004` — those issues document the fail-boilerplate and dispatch duplication symptoms; landing this issue removes both wholesale, so they close without action.
- `blocks: TEST-003` — the consolidated lifecycle test described there must target the new runner, not the three legacy functions.
- `related: BUG-001, BUG-010, BUG-012, BUG-015` — these bugs live inside the code being consolidated. They can be fixed before or after, but fixing them *during* the consolidation is cheapest; their specs are written against current files and note the post-ARCH-001 location.
- `related: ARCH-007` — the agent-chat loop is the fourth orchestration script; it stays separate because its lifecycle (interactive, WS-driven) genuinely differs.
