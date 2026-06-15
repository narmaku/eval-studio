---
id: BUG-010
title: Raw exception text is persisted into Result.judge_reasoning while the same error is sanitized for WebSocket clients
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
related: [ARCH-001, SEC-001]
child_of: null
affected_paths:
  - backend/app/services/evaluation_service.py
  - backend/app/services/arena_evaluation_service.py
  - backend/app/services/rag_evaluation_service.py
---

## Problem
When an item errors, all three eval services broadcast a *sanitized* message over WS but store the *raw* `str(exception)` into `Result.judge_reasoning` — which is then returned verbatim by `GET /results` and rendered in the results UI, and serialized into the downloadable `results.json` artifact. Raw LLM/provider exceptions routinely embed request URLs, header dumps, and occasionally key fragments.

## Evidence
- `backend/app/services/evaluation_service.py:270-282`: sanitized for broadcast (`:273`) but `judge_reasoning=str(r)` (`:281`).
- Same pattern: `arena_evaluation_service.py:300-311` and `rag_evaluation_service.py:296-307`.
- Exposure paths: `ResultResponse.model_validate` (`api/v1/results.py:55`), artifact serialization `services/artifact_generation.py:83`.
- Contrast with the sanitization contract the codebase otherwise enforces: `core/exceptions.py:56-82`.

## Impact
Inconsistent application of the project's own secret/internal-detail hygiene; whatever `sanitize_error_for_client` exists to hide ends up in the DB, the REST API, and downloadable artifacts anyway.

## Root cause
The Result construction predates the sanitization helper; only the broadcast call was updated.

## Proposed fix (specification)
In all three error-result constructions, replace `judge_reasoning=str(r)` with `judge_reasoning=sanitize_error_for_client(r)`. Keep the raw text in server logs (already done via `logger.error(..., error=str(r))` on the preceding lines). Post-ARCH-001 there is exactly one such construction site.

## Alternatives considered
Add a separate `error` column on Result for sanitized error vs reasoning — cleaner semantics, but schema churn not justified yet; note for DATA work if results modeling is revisited.

## Verification
Unit: in `tests/unit/test_evaluation_service.py`, make `call_model` raise `RuntimeError("secret-path /home/x")` → stored Result.judge_reasoning equals the generic message, not the secret string.

## Relationship notes
- `related: ARCH-001` — fix lands ×3 now or ×1 after consolidation; do it during ARCH-001 if that lands promptly.
- `related: SEC-001` — same "secrets escape via results/artifacts" theme; SEC-001 covers config-borne secrets, this covers exception-borne ones.
