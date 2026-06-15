---
id: SIMP-005
title: EvaluationAdapter ABC carries unused surface (supports_mode, get_available_metrics, config schema hooks)
category: simplification
severity: low
effort: XS
confidence: high
breaking: false
status: open
depends_on: []
blocks: []
supersedes: []
superseded_by: [SIMP-002]
conflicts_with: []
related: []
child_of: null
affected_paths:
  - backend/app/adapters/base.py
  - backend/app/adapters/litellm_judge.py
---

## Problem
The adapter ABC mandates `supports_mode()` and `get_available_metrics()` — neither has a single caller — and offers `get_default_config()` (also uncalled; `get_config_schema` is called only by the evaluators discovery API). Abstract methods without consumers force every (hypothetical) future adapter to implement dead interface.

## Evidence
- `grep -rn "supports_mode\|get_available_metrics" backend/app --include="*.py" | grep -v "adapters/base.py\|litellm_judge.py"` → empty (definitions/implementations only).
- `get_default_config` callers: `grep -rn "get_default_config" backend/app` → only base + litellm_judge definitions.
- `get_config_schema` sole caller: `api/v1/evaluators.py:36-48`.

## Impact
~60 lines of dead contract + implementation (`litellm_judge.py:96-141, 409-425`); misleads about what the system actually consults when "supporting" a mode (it consults `config/evaluators.yaml`'s `modes` list instead, `adapters/registry.py:101-107`).

## Root cause
Interface designed speculatively before usage patterns existed.

## Proposed fix (specification)
If SIMP-002 (delete registry machinery) lands, fold this in there: DELETE `supports_mode`, `get_available_metrics`, `get_default_config`, and `get_config_schema` from `adapters/base.py` and their implementations in `litellm_judge.py` (the discovery API that called `get_config_schema` is deleted by SIMP-002 anyway). Standalone (if SIMP-002 is rejected in favor of BUG-018): delete the first three, keep `get_config_schema`.

## Alternatives considered
Wire `supports_mode` into evaluation creation validation — rejected: the YAML `modes` list already serves that need at the registry level.

## Verification
`uv run pytest tests/unit/test_litellm_adapter.py` green; grep shows no remaining references.

## Relationship notes
- `superseded_by: SIMP-002` — fully contained in its step 5; this record exists for the SIMP-002-rejected branch, where the trim still applies (minus `get_config_schema`).
