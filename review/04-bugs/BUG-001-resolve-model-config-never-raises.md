---
id: BUG-001
title: resolve_model_config never raises, making three except-ValueError guards dead and arena contestant skipping inoperative
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
conflicts_with: []
related: [ARCH-001]
child_of: null
affected_paths:
  - backend/app/services/provider_utils.py
  - backend/app/services/evaluation_service.py
  - backend/app/services/arena_evaluation_service.py
  - backend/app/agent_backends/factory.py
---

## Problem
`resolve_model_config`'s docstring promises `Raises: ValueError: If no model can be resolved from any source`, but the body explicitly converts the no-model case into `model = ""` and returns. Consequently: (a) the QA service's "Model resolution failed" early-exit is unreachable; (b) the arena service's per-contestant `except ValueError: continue` ("Mark this contestant as unresolvable — we'll skip it") never skips anything — an unresolvable contestant proceeds with `model=""` and fails on every item at LLM-call time; (c) the agent factory's documented resolution failure can't happen.

## Evidence
- `backend/app/services/provider_utils.py:56-60` (docstring "Raises ValueError"), vs `:111-112`:
  ```python
  if not model:
      model = ""
  ```
  and `:123-124` `return ResolvedModel(model=model or "", ...)` — no raise anywhere in the function.
- Dead guard (QA): `backend/app/services/evaluation_service.py:94-102`.
- Inoperative skip (arena): `backend/app/services/arena_evaluation_service.py:141-154`.
- Dead doc (agent factory): `backend/app/agent_backends/factory.py:24` ("Raises ValueError … if model resolution fails").

## Impact
A misconfigured evaluation (no provider, no model, no default) runs to completion as a sea of per-item errors instead of failing fast with "Model resolution failed"; in arena mode a typo'd contestant silently drags the whole run instead of being skipped with a log line. Error surfaces are confusing and slow.

## Root cause
The empty-string fallback was added (probably for custom providers, which use `endpoint_url` and legitimately have `model=""`) without preserving the error contract for the litellm path.

## Proposed fix (specification)
1. In `resolve_model_config` (`provider_utils.py`), after the settings fallback, raise for the truly-unresolvable case while keeping custom providers valid:
   ```python
   if not model and provider_type != "custom":
       raise ValueError("No model could be resolved (no provider_id, model, or DEFAULT_MODEL fallback)")
   ```
   (custom providers must still pass `endpoint_url`; add `if provider_type == "custom" and not endpoint_url: raise ValueError(...)`.)
2. Remove the now-redundant `model = ""` branch (`:111-112`).
3. The three existing `except ValueError` guards become live and need no change; arena's skip path now actually skips, and its existing `< 2 resolved contestants` check (`arena_evaluation_service.py:156-168`) does its job.
4. Check `score_session` (`api/v1/sessions.py:193`) which also calls `resolve_model_config`: wrap with a 422 `ValidationException` on ValueError so a missing judge model returns a clean client error.

## Alternatives considered
Return a sentinel and check at call sites — rejected: the call sites already expect the exception; honor the written contract.

## Verification
- New unit tests in `tests/unit/test_provider_utils.py`: empty config + no settings → raises; custom provider without model → resolves; custom without endpoint_url → raises.
- Integration: create QA eval with empty `model_endpoint` and no DEFAULT_MODEL → evaluation status `failed`, error "Model resolution failed" with zero Result rows.

## Relationship notes
- `related: ARCH-001` — the QA/arena guard code moves into the consolidated runner; this fix is independent and should land first (it changes observable behavior the consolidation must preserve).
