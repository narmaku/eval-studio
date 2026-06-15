---
id: TEST-002
title: Test files pin dead code in place (dead Provider ORM, dead registry machinery, dead BuiltinHarness)
category: testing
severity: low
effort: S
confidence: high
breaking: false
status: open
depends_on: [ARCH-002, SIMP-002, SIMP-003]
blocks: []
supersedes: []
superseded_by: []
conflicts_with: []
related: []
child_of: null
affected_paths:
  - backend/tests/unit/test_provider_model.py
  - backend/tests/unit/test_evaluator_registry.py
  - backend/tests/unit/test_eval_adapter_factory.py
  - backend/tests/unit/test_evaluator_config_files.py
  - backend/tests/unit/test_harness_factory.py
---

## Problem
Several test modules exist to exercise code this review marks for deletion: the dead `Provider` ORM model, the evaluator registry/factory/config-file subsystem, and `BuiltinHarness`. Green tests over dead code are worse than no tests — they create the illusion of a live, supported feature and add friction ("tests will break") to exactly the deletions that should happen.

## Evidence
- `backend/tests/unit/test_provider_model.py` — targets the ORM with zero runtime consumers (ARCH-002 evidence).
- `backend/tests/unit/test_evaluator_registry.py`, `test_eval_adapter_factory.py`, `test_evaluator_config_files.py` — target machinery whose runtime dispatch never fires (SIMP-002/BUG-018 evidence).
- `backend/tests/unit/test_harness_factory.py` — includes BuiltinHarness instantiation cases (SIMP-003).

## Impact
Maintenance cost and false confidence; the suite's size overstates real coverage of live paths (which have gaps — TEST-003).

## Root cause
Tests written conscientiously alongside features whose runtime wiring was never completed or later abandoned.

## Proposed fix (specification)
Delete each test module together with its target (the owning issues' deletion lists already include them):
- with ARCH-002: `test_provider_model.py` (+ any `resolve_provider` cases inside `test_providers.py`/`test_provider_utils.py`).
- with SIMP-002: the three evaluator test modules.
- with SIMP-003: BuiltinHarness cases from `test_harness_factory.py`.
If BUG-018 (wire it) wins over SIMP-002, the evaluator tests stay and instead gain the missing dispatch assertions (factory called with `config.evaluator_id`).

## Alternatives considered
Keep tests as deletion canaries — that's what this issue file is for; the tests cost more.

## Verification
Post-deletions: `uv run pytest` green; `uv run pytest --collect-only -q | wc -l` drops accordingly; no orphaned fixtures remain (`grep -rn "evaluator" backend/tests` clean under SIMP-002).

## Relationship notes
- `depends_on: ARCH-002, SIMP-002, SIMP-003` — each tranche of test deletion is only valid once its production-code deletion lands (deleting tests first would drop coverage on still-live code).
