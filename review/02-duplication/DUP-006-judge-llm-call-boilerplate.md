---
id: DUP-006
title: LiteLLM judge call assembly + JSON parsing + error fallback triplicated inside the judge adapter
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
related: [BUG-012, BUG-013, ARCH-001]
child_of: null
affected_paths:
  - backend/app/adapters/litellm_judge.py
---

## Problem
`evaluate_qa`, `evaluate_conversation`, and `evaluate_rag` each re-implement the same sequence: build `litellm.acompletion` kwargs (model/messages/temperature/response_format + api_key/api_base + extra_params merge), call, handle `content is None`, `json.loads` with error fallback. Only the prompt and the score-extraction differ.

## Evidence
- kwargs assembly: `backend/app/adapters/litellm_judge.py:172-186` (qa), `:271-285` (conversation), `:346-360` (rag) — including the identical `for k, v in self.extra_params.items(): if k not in kwargs:` merge loop.
- empty-content + parse-error fallbacks: `:188-199`, `:288-300`, `:363-383` — same structure, different fallback shapes.

## Impact
The triplication is why two real bugs could grow in one file: the RAG path hardcodes `temperature: 0.0` and threshold 0.7 while the others honor judge config (BUG-012), and adding proxy/SSL support (BUG-013) needs three edits.

## Root cause
Each evaluate_* method written by copying the previous one.

## Proposed fix (specification)
1. Add `async def _ask_judge(self, prompt: str, judge_config: JudgeConfigParams | None) -> dict | None` that builds kwargs (model/temperature from judge_config or defaults, key/base, extra_params, `response_format=json_object`), calls litellm inside the proxy/SSL context (BUG-013's fix lands here once), and returns the parsed dict or `None` on empty/unparseable content (logging as today).
2. The three evaluate_* methods become: format prompt → `result = await self._ask_judge(...)` → mode-specific Score extraction with their existing fallback Scores when `result is None`.
3. Pass `judge_config` into `evaluate_rag` so its temperature/threshold come from the same source (coordinates with BUG-012; signature change is internal — update `rag_evaluation_service.py` call and ABC in `adapters/base.py:97-104`).

## Alternatives considered
Decorator-based retry/parse wrapper — rejected: a plain private method is simpler and sufficient.

## Verification
`uv run pytest tests/unit/test_litellm_adapter.py tests/unit/test_conversation_judge.py tests/unit/test_rag_judge.py` green; add one test asserting extra_params don't override explicit kwargs (existing behavior, `:183-185`).

## Relationship notes
- `related: BUG-012, BUG-013` — both bugs are fixed *in* the helper this issue creates; implement together to avoid double-touching the file.
- `related: ARCH-001` — independent; ARCH-001 consolidates the callers, this consolidates the adapter internals.
