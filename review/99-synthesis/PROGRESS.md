# Review Fix Progress

Tracks session-by-session progress implementing the deep-quality review.
Review at commit `ffc4b27` (branch `main`), 94 issues across 13 categories.

## Status board
- Done: INFRA-007, INFRA-008, BUG-004, BUG-003, BUG-005, BUG-017, BUG-007, BUG-010, BUG-009, INFRA-002, BUG-006 (superseded)
- In progress / partial: —
- Next recommended (ready, priority order): BUG-012, BUG-014, BUG-015+PERF-004, SIMP-003, SIMP-007, INFRA-006, CONS-001, DUP-001, DUP-005, API-001
- Toolchain baseline as of 2026-06-15: backend pytest 915 passed, ruff 0 errors, format 0 files, frontend 606 passed, lint 6 warnings (not errors), build succeeds

---

## Session 2 — 2026-06-15 — claude-opus-4-6[1m]

### Baseline observed
- Backend tests: 900 passed (pre-session; 915 with new tests)
- Backend lint: 0 errors (INFRA-007 merged on main)
- Backend format: 0 files to reformat
- Frontend tests: 606 passed
- Frontend lint: 6 warnings (not errors)
- Frontend build: succeeds (INFRA-008 merged on main)
- Graph validator: green

### Scope chosen + why
7 XS Phase 0 quick wins from the backend correctness batch (items 1–5, 9 of QUICK-WINS.md):
**BUG-004, BUG-003, BUG-005+BUG-017 (paired, same file), BUG-007, BUG-010, BUG-009**.

All are dependency-free, user-visible correctness fixes, and the session 1 handoff recommended
this exact batch. Combined effort ≈ 7×XS, fits one session comfortably.

### Changes

**BUG-004** — `backend/app/harnesses/registry.py:102`: changed `parent.parent.parent` → `parents[3]`.
Harness config discovery now reaches the repo root correctly.

**BUG-003** — `backend/app/core/registry_base.py:83-87`: wrapped `_parse_item()` call in
`try/except (KeyError, TypeError, ValueError)` with a structured log warning. A malformed
YAML entry now skips with a warning instead of crashing the entire registry load.

**BUG-005+BUG-017** — `backend/app/agent_backends/custom_httpx_agent.py`:
- `_build_request_body`: `json.dumps(msg)[1:-1]` escaping before substitution + `try/except
  json.JSONDecodeError → ValueError` wrapping.
- `extract_json_path`: wrapped indexing in `try/except → ValueError` naming the path and segment.
- `backend/app/api/v1/providers.py:167`: same escape applied in test_connection.

**BUG-007** — `backend/app/api/v1/providers.py:219`: added `single_model=payload.single_model`
to `create_provider`. `backend/app/core/providers.py:87`: changed conditional serialization to
unconditional `"single_model": item.single_model`. Value now persists through create and survives
YAML reload.

**BUG-010** — `backend/app/services/evaluation_service.py:281`,
`arena_evaluation_service.py:310`, `rag_evaluation_service.py:307`: replaced `str(r)` with
`sanitize_error_for_client(r)` in error-Result `judge_reasoning` construction.

**BUG-009** — `backend/app/rag_backends/base.py:55-57`: added `close()` no-op default to ABC.
`backend/app/services/rag_evaluation_service.py:66,350-352`: initialized `rag_adapter = None`
before outer try, added `finally: if rag_adapter: await rag_adapter.close()`.

**Tests added** (15 new tests, 900 → 915):
- `test_yaml_backed_registry.py`: 2 tests for BUG-003 (KeyError skip + reload skip)
- `test_custom_httpx_adapter.py`: 7 tests for BUG-005/017 (escaping: quotes, newlines,
  backslashes, injection; invalid template; path error wrapping; type error on None)
- Updated 2 existing extract_json_path tests (KeyError/IndexError → ValueError)
- `test_providers.py`: 2 tests for BUG-007 (serialization + reload persistence)
- `test_evaluation_service.py`: 1 test for BUG-010 (sanitized judge_reasoning)
- `test_harness_registry.py`: 1 test for BUG-004 (path resolution)
- `test_rag_evaluation_service.py`: 2 tests for BUG-009 (close on success + failure)

**Files modified:**
- backend/app/harnesses/registry.py
- backend/app/core/registry_base.py
- backend/app/agent_backends/custom_httpx_agent.py
- backend/app/api/v1/providers.py
- backend/app/core/providers.py
- backend/app/services/evaluation_service.py
- backend/app/services/arena_evaluation_service.py
- backend/app/services/rag_evaluation_service.py
- backend/app/rag_backends/base.py
- tests/unit/test_custom_httpx_adapter.py
- tests/unit/test_yaml_backed_registry.py
- tests/unit/test_providers.py
- tests/unit/test_evaluation_service.py
- tests/unit/test_harness_registry.py
- tests/unit/test_rag_evaluation_service.py

Branch: `fix/review-phase0-bugs-batch1`

### Verification
- Backend pytest: 915 passed (was 900, +15 new tests)
- Backend ruff check: 0 errors
- Backend ruff format: 0 files to reformat
- Frontend tests: 606 passed (unchanged)
- Frontend lint: 6 warnings (unchanged)
- Frontend build: succeeds (unchanged)
- Graph validator: green
- No regressions. All new tests verify the specific fix per issue specs.

### Graph/roadmap updates
- BUG-003, BUG-004, BUG-005, BUG-007, BUG-009, BUG-010, BUG-017: status → done
- No supersession changes needed (none of these supersede other issues)

### New issues discovered
None.

### Addendum: INFRA-002 (fresh-DB startup crash)

CI Container Smoke Test was failing on main (pre-existing). Root cause: app lifespan never
ran Alembic migrations, so fresh databases had no tables. Fixed by adding `_run_alembic_migrations()`
to the lifespan (runs via `asyncio.to_thread` to avoid nested event loop conflict with alembic's
`asyncio.run`). Guarded for tests (`sqlite+aiosqlite://` in-memory URL skipped). Verified with
fresh temp DB + health check. BUG-006 auto-closes (superseded by INFRA-002).

Files modified: `backend/app/main.py`

### Breaking changes
None. All fixes are internal behavioral corrections — no API or schema changes.

### Handoff / next session should start with
Continue Phase 0 quick wins. Next highest-impact items:
1. **BUG-012** (XS) — RAG judge hardcodes threshold/temperature
2. **BUG-014** (XS) — Rubric generate/refine never pass API key
3. **BUG-015 + PERF-004** (XS batch) — Rerun keeps stale artifacts + bulk delete results
4. **SIMP-003** (XS) — Delete BuiltinHarness
5. **SIMP-007** (XS) — Delete examples/judges/ (+ DOC-004 auto-closes)
6. **INFRA-006** (XS) — Rewrite providers.yaml.example
7. **CONS-001** (S) — Fix .env.example drift
8. **DUP-001** (XS) — Consolidate _utcnow/_iso_now
9. **DUP-005** (XS) — Consolidate WS broadcast
10. **API-001** (XS) — Fix rubrics pagination params

All remaining Phase 0 items. A session taking 5–8 of these would complete Phase 0.

---

## Baseline (recorded session 1, 2026-06-15)

| Gate | Status | Notes |
|------|--------|-------|
| Backend tests | **900 passed** | Green |
| Backend lint (ruff check) | **5 errors** | All in `alembic/versions/1307fd3f3b27_…py` — INFRA-007 |
| Backend format (ruff format) | **1 file** | Same migration file — INFRA-007 |
| Frontend tests | **606 passed** | Green |
| Frontend lint (eslint) | **6 warnings** | All `react-hooks/incompatible-library` (TanStack Table) — not errors |
| Frontend build (tsc + vite) | **18 tsc errors** | INFRA-008 — `exportPdf.ts` (8), `AgentEvaluation.tsx` (1), `evaluationStore.test.ts` (6), `providerStore.test.ts` (1), `resultStore.test.ts` (2) |
| Graph validator | **Green** | `check_graph.py` passes |

Note: The review documented 5 tsc errors (store tests only). The actual count is 18,
including `exportPdf.ts` and `AgentEvaluation.tsx`. All must be fixed for `npm run build`
to pass.

---

## Session 1 — 2026-06-15

### Scope (chosen before coding)

**INFRA-008** (S, high) — Fix all 18 tsc errors to make `npm run build` pass.
Highest priority: unblocks production image build, docker-based verification, CI.

**INFRA-007** (XS, low) — Fix 5 ruff lint errors + 1 format issue in migration file.
Unblocks clean `make lint` for all contributors.

**Rationale:** These two issues are the #1 and #2 items in the Phase 0 quick-wins list.
INFRA-008 is explicitly marked "do this one first" in QUICK-WINS.md. No dependencies.
Combined effort ≈ S+XS, well within one session.

### Work log

- **INFRA-007**: `ruff check --fix . && ruff format .` on migration file. Updated
  `script.py.mako` to emit modern `|` unions and sorted imports, preventing regressions
  in future autogenerated migrations. Commit `25ab101`.
- **INFRA-008**: Fixed all tsc errors across 15 files (17 files total with INFRA-007).
  The review documented 5 errors in 3 store test files; actual count was ~30+ errors
  across 15 files (tsc reports in waves — fixing one batch reveals the next). Categories:
  - Store test fixtures missing `average_score`/`pass_rate` (6 sites in evaluationStore.test.ts)
  - Provider fixtures missing `single_model: boolean` and using `null` for `request_body_template: string` (5 test files + 1 component)
  - Array index accesses without non-null assertions under `noUncheckedIndexedAccess` (exportPdf.ts, resultStore.test.ts, ResultDetailView.test.tsx, exportPdf.test.ts)
  - `listProviders()` called with spurious argument in ProviderSelector.tsx and JudgeConfigPanel.tsx
  - `RetrievedChunk` fixture used `score` instead of `relevance_score` (RAGResultsTable.test.tsx)
  - `provider_id` possibly undefined in AgentEvaluation.tsx
  - Mock typing for exportResultsPdf (ResultDetailView.test.tsx)
  Commit `7671cb9`.

### Result

**INFRA-007: DONE.** Backend lint and format clean.
**INFRA-008: DONE.** `npm run build` succeeds. Production image frontend stage unblocked.

Post-fix gate:

| Gate | Status |
|------|--------|
| Backend tests | 900 passed |
| Backend lint | 0 errors |
| Backend format | 0 files to reformat |
| Frontend tests | 606 passed |
| Frontend lint | 6 warnings (unchanged, not errors) |
| Frontend build | **0 errors, build succeeds** |
| Graph validator | Green |

Branch: `fix/review-infra-007-008` (2 commits, ready to merge to main).

**Breaking changes:** None. All fixes are in test fixtures, non-null assertions, and
removing spurious function arguments — no API or behavioral changes.

---

## Completed issues

| ID | Session | Commit | Notes |
|----|---------|--------|-------|
| INFRA-007 | 1 | `25ab101` | + mako template fix to prevent regressions |
| INFRA-008 | 1 | `7671cb9` | Actual error count was ~30+, not 5 as documented |
| BUG-004 | 2 | (pending) | parents[3] path fix |
| BUG-003 | 2 | (pending) | Base class try/except wraps all registries |
| BUG-005 | 2 | (pending) | JSON-escaped template substitution |
| BUG-017 | 2 | (pending) | extract_json_path error wrapping |
| BUG-007 | 2 | (pending) | single_model passed through + always serialized |
| BUG-010 | 2 | (pending) | sanitize_error_for_client in all 3 services |
| BUG-009 | 2 | (pending) | RAG adapter close() in finally |
| INFRA-002 | 2 | (pending) | Alembic migrations at startup |
| BUG-006 | 2 | — | Superseded by INFRA-002 |

---

## Next recommended issue(s)

See Status board and Session 2 handoff above.
