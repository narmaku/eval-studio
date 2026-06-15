---
id: SIMP-003
title: Delete BuiltinHarness — self-documented dead code
category: simplification
severity: low
effort: XS
confidence: high
breaking: false
status: open
depends_on: []
blocks: [TEST-002]
supersedes: []
superseded_by: []
conflicts_with: []
related: [ARCH-007]
child_of: null
affected_paths:
  - backend/app/harnesses/builtin.py
  - backend/app/harnesses/factory.py
  - config/harnesses.yaml.example
---

## Problem
`BuiltinHarness` exists, per its own module docstring, only "so that the factory can instantiate it if needed in the future"; its `send_message` yields a literal "BuiltinHarness.send_message is not used at runtime." The real builtin path bypasses the harness layer inside `agent_chat_service` (dispatch happens only when `profile.type == "subprocess"`).

## Evidence
- `backend/app/harnesses/builtin.py:1-7` (docstring admission), `:35-40` (stub yield).
- Dispatch ignores builtin profiles: `services/agent_chat_service.py:88-95` (only `type == "subprocess"` routes to a harness; everything else falls through to the direct adapter path).
- Factory branch: `harnesses/factory.py:24-27`.

## Impact
~45 lines of intentional dead code plus a factory branch and example-config entry that imply an abstraction boundary the runtime doesn't honor — actively misleading for anyone studying the harness system.

## Root cause
Harness abstraction introduced for subprocess agents; a builtin placeholder was added for registry symmetry.

## Proposed fix (specification)
1. DELETE `backend/app/harnesses/builtin.py`; remove the `"builtin"` branch from `create_harness` (`factory.py:24-27`) → unknown types raise (registry entries with `type: builtin` remain listable for UI labeling; they just aren't instantiable, matching reality).
2. Keep the `builtin-litellm` entry in `config/harnesses.yaml.example` (the UI uses it to label the default path) but fix its description if needed; alternatively gate `create_harness` calls on `type == "subprocess"` only — which `agent_chat_service.py:92` already does.
3. DELETE the builtin cases from `tests/unit/test_harness_factory.py`.

## Alternatives considered
Make the builtin path actually run through BuiltinHarness (true abstraction) — rejected per ARCH-007's alternative analysis: one implementation doesn't justify routing the hot path through an adapter that adds nothing.

## Verification
`uv run pytest tests/unit/test_harness_factory.py tests/unit/test_subprocess_harness.py tests/integration/test_agent_chat_ws.py` green; builtin chat still works (it never touched this class).

## Relationship notes
- `related: ARCH-007` — both touch the agent path's structure; no ordering constraint.
