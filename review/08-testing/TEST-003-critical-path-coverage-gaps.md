---
id: TEST-003
title: Critical paths without meaningful coverage: fresh-install boot, run-lifecycle invariants, WS protocol conformance, production serving
category: testing
severity: medium
effort: M
confidence: medium
breaking: false
status: open
depends_on: [ARCH-001, ARCH-003, INFRA-001, INFRA-002]
blocks: []
supersedes: []
superseded_by: []
conflicts_with: []
related: [TEST-001]
child_of: null
affected_paths:
  - backend/tests/
  - .github/workflows/ci.yml
  - frontend/src/stores/sessionStore.test.ts
---

## Problem
The suite is broad (≈75 backend test files) but four load-bearing behaviors have no test at all, and each corresponds to a defect found in this review — i.e., precisely the untested spots rotted:
1. **Fresh-install boot**: nothing starts the app against an empty database (BUG-006/INFRA-002 would have been caught by one test).
2. **Run-lifecycle invariants across modes**: per-mode tests exist, but no shared parametrized contract (pending→running→terminal; all-fail ⇒ failed; concurrent-trigger single execution per BUG-016) — drift between the three copies (BUG-012 et al.) went unnoticed.
3. **WS chat protocol conformance**: backend envelope tests and FE store tests each test their *own* protocol understanding; nothing asserts they match (ARCH-003's `message_id` drift lived happily on both sides' green tests).
4. **Production serving**: CI's container smoke checks only `/api/v1/health`, so a production image whose UI is unreachable (INFRA-001) passes.

## Evidence
- `grep -rn "lifespan\|migrate" backend/tests` → no startup-against-empty-DB test (conftest bypasses startup by creating tables itself, `tests/conftest.py:29-36`).
- No parametrized cross-mode lifecycle test: per-mode files only (`test_evaluation_service.py`, `test_arena_evaluation_service.py`, `test_rag_evaluation_service.py`).
- FE protocol fixtures hand-written with `message_id` (`frontend/src/stores/sessionStore.test.ts` — passes against types, not against the backend).
- CI smoke: `.github/workflows/ci.yml:95-114` (curls health only).

## Impact
The classes of bug this review found dynamically-adjacent (boot crash, protocol drift, prod UI 404) regenerate freely; tests scoped to the current triplicated structure can't express the invariants.

## Root cause
Tests written per-module as features landed; no contract-level tests, and the structures needed for them (single runner, typed protocol) didn't exist.

## Proposed fix (specification)
Scoped to the TARGET architecture (hence the dependencies):
1. **Boot test** (after INFRA-002): `tests/integration/test_startup.py` — run migrations via the new startup hook against a tmp-file SQLite URL, instantiate the app lifespan, hit /health. No mocking.
2. **Lifecycle contract** (after ARCH-001): one parametrized test over `MODE_RUNNERS` keys asserting: status transitions, all-items-fail ⇒ failed with error, partial-fail ⇒ completed, CAS claim rejects a second concurrent start (BUG-016 regression), artifacts generated on completion.
3. **Protocol conformance** (after ARCH-003): export the Pydantic WS envelope JSON-schemas in a small snapshot file; an FE vitest validates its fixtures against the snapshot (checked-in, regenerated alongside ARCH-004's OpenAPI snapshot).
4. **Smoke depth** (after INFRA-001): extend the CI smoke to `curl -sf localhost:8000/` and assert HTML content-type, plus one authenticated-mode boot (`AUTH_DISABLED=false` + bootstrap key create).

## Alternatives considered
Writing these against today's structure — explicitly rejected per review ground rules: tests for the triplicated services would be rewritten by ARCH-001 weeks later.

## Verification
The four new test files/jobs exist and fail when their respective defects are re-introduced (mutation check: revert INFRA-001's static mount → smoke fails).

## Relationship notes
- `depends_on: ARCH-001, ARCH-003, INFRA-001, INFRA-002` — each numbered item targets the post-fix structure (see spec); partial implementation is fine as its dependency lands.
- `related: TEST-001` — fixture-layer health affects all of the above.
