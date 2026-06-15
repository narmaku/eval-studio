---
id: TEST-001
title: Test isolation reaches into registry privates and forgets the evaluator registry
category: testing
severity: low
effort: S
confidence: high
breaking: false
status: open
depends_on: []
blocks: []
supersedes: []
superseded_by: []
conflicts_with: []
related: [ARCH-005, SIMP-002]
child_of: null
affected_paths:
  - backend/tests/conftest.py
  - backend/app/core/registry_base.py
---

## Problem
The autouse `_isolate_yaml_registries` fixture protects real config files (per CLAUDE.md pitfall 8) by directly mutating four private attributes on three registry singletons (`_items`, `_config_path`, `_last_mtime`, plus calling `_persist_yaml`). It omits the fourth registry (`evaluator_registry`), which therefore reads the real `config/evaluators.yaml` during tests — read-only today, but the isolation contract is incomplete and the private-attribute coupling breaks on any registry refactor (ARCH-005 touches exactly these internals).

## Evidence
- `backend/tests/conftest.py:60-99` — list contains `provider_registry, tool_server_registry, harness_registry` (`:67`); evaluator registry absent; private access throughout (`:78-90`).
- Evaluator registry is YAML-backed the same way: `backend/app/adapters/registry.py:176-179`.
- CLAUDE.md pitfall 8: "Tests must NEVER use actual config file paths".

## Impact
Tests that list evaluators depend on repo-state config (they'd change behavior if someone edits `config/evaluators.yaml`); registry-internal refactors will break the entire test suite's fixture layer rather than a public seam.

## Root cause
No public test seam on `YAMLBackedRegistry`; fixture written against internals; evaluator registry added later (or earlier) than the fixture list.

## Proposed fix (specification)
1. Add a public context manager to `YAMLBackedRegistry`:
   ```python
   @contextmanager
   def isolated(self, path: Path):
       """Swap state to an empty registry at `path`; restore on exit. For tests."""
   ```
   implementing exactly what the fixture does today (snapshot/replace/restore).
2. Rewrite `_isolate_yaml_registries` to use it with `contextlib.ExitStack`, and include `evaluator_registry` in the list (tests needing the litellm-judge entry seed it explicitly, mirroring the `__test__` provider seeding at `:83-90`).
3. If SIMP-002 deletes the evaluator registry, the list shrinks back to three — the fixture change is still right.

## Alternatives considered
Dependency-inject registries per test — the "proper" fix but a large refactor (module-level singletons everywhere); the public seam is proportionate.

## Verification
`uv run pytest` green; mutate `config/evaluators.yaml` locally → no test behavior change (today `tests/unit/test_evaluator_registry.py` may notice).

## Relationship notes
- `related: ARCH-005` — registry internals change there; the public seam shields tests from it; land this first or together.
- `related: SIMP-002` — removes one registry from scope.
