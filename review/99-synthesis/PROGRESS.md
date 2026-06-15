# Review Fix Progress

Tracks session-by-session progress implementing the deep-quality review.
Review at commit `ffc4b27` (branch `main`), 94 issues across 13 categories.

## Status board
- Done: INFRA-007, INFRA-008, BUG-003, BUG-004, BUG-005, BUG-007, BUG-009, BUG-010, BUG-012, BUG-014, BUG-015, BUG-017, INFRA-001, INFRA-002, INFRA-003, INFRA-004, INFRA-006, SIMP-003, SIMP-007, DUP-001, DUP-005, API-001, DATA-002, DATA-004, PERF-002, PERF-004, CONS-001, CONS-006, ARCH-002, ARCH-008, SIMP-001, SIMP-002, BUG-006 (superseded), DOC-004 (superseded by SIMP-007), CONS-007 (superseded by ARCH-002), FE-005 (superseded by SIMP-001), DOC-003 (superseded by SIMP-001), SIMP-005 (superseded by SIMP-002), BUG-018 (closed, conflict loser to SIMP-002)
- In progress / partial: —
- **Phase 1 continues.** Next: SEC-001 (high), SIMP-004 (medium), ARCH-001 (high, L), ARCH-006 (high, S)
- Toolchain baseline as of 2026-06-15: backend pytest 868 passed, ruff 0 errors, format 0 files, frontend 562 passed (53 files), lint 6 warnings (not errors), build succeeds

---

## Session 5 — 2026-06-15 — claude-opus-4-6[1m]

### Baseline observed
- Backend tests: 915 passed
- Backend lint: 0 errors
- Backend format: 195 files already formatted
- Frontend tests: 607 passed (57 files)
- Frontend lint: 6 warnings (not errors)
- Frontend build: succeeds
- Graph validator: green

### Scope chosen + why
Three Phase 1 structural deletions, all dependency-free and high-impact:

1. **SIMP-001** (M, high, breaking) — Delete the environments vertical (~900 lines of stubs/501s/dead infra). Closes FE-005, DOC-003.
2. **SIMP-002** (M, high, breaking) — Delete evaluator registry machinery (~1,400 lines). Closes SIMP-005, resolves BUG-018 conflict.
3. **ARCH-008** (S, medium) — Move `_migrate_scored_sessions` to Alembic data migration, delete from lifespan. Now effectively XS since `_migrate_single_model_providers` was deleted in session 4.

Reasoning: These are the highest-impact ready Phase 1 items after INFRA-001/ARCH-002 (done). All are pure deletion with clear specs. SEC-001 (next priority) benefits from landing after this cleanup. Two M + one XS fits one session.

### Changes

**SIMP-001** — Deleted the entire environments vertical:
- DELETED: `backend/app/environments/` (base.py, byoe.py, __init__.py), `backend/app/api/v1/environments.py`, `backend/app/models/environment.py`, `backend/app/schemas/environment.py`
- DELETED: `frontend/src/pages/Environments.tsx`, `frontend/src/types/environment.ts`
- DELETED: `environments/compose/`, `environments/tmt/`, `environments/ansible/`, `environments/scenarios/`
- Removed `Environment` model export from `models/__init__.py`
- Removed environments router from `main.py`
- Removed `asyncssh` dependency from `pyproject.toml`
- Removed `environment_id` from: `Evaluation` model, `EvaluationCreate`/`EvaluationResponse` schemas, `RunRequest` schema, both `evaluations.py` create calls
- Removed FE: environment API methods + type imports from `api.ts`, nav entry from `TopNav.tsx`, route + lazy import from `App.tsx`, re-export from `types/index.ts`
- Removed `environment_id` from FE types: `Evaluation`, `EvaluationConfig`, `CreateEvaluationRequest` (evaluation.ts), `CreateSessionRequest` (session.ts)
- Removed `environment_id: null` from all 5 test fixtures in `evaluationStore.test.ts`
- Removed `'Environments'` assertion from `App.test.tsx`
- Added Alembic migration `346b00c58bbe`: `DROP COLUMN environment_id` from evaluations, `DROP TABLE environments`
- Rewrote `docs/docs/environments.md` to "not yet built" placeholder

**SIMP-002** — Deleted evaluator registry machinery:
- DELETED: `backend/app/adapters/registry.py`, `backend/app/adapters/factory.py`, `backend/app/api/v1/evaluators.py`, `config/evaluators.yaml`
- DELETED backend tests: `test_evaluator_registry.py`, `test_eval_adapter_factory.py`, `test_evaluator_config_files.py`
- DELETED FE: `EvaluatorSelector.tsx(+test)`, `EvaluatorList.tsx(+test)`, `EvaluatorDetail.tsx(+test)`, `evaluatorStore.ts(+test)`, `types/evaluator.ts`
- Three service call sites (`evaluation_service.py`, `arena_evaluation_service.py`, `rag_evaluation_service.py`): replaced `create_evaluation_adapter()` with direct `LiteLLMJudgeAdapter(...)` construction
- Removed evaluator router from `main.py`
- Removed `evaluator_config_dir` from `core/config.py`
- Removed `EVALUATORS_CONFIG_PATH` and `EVALUATOR_CONFIG_DIR` from `.env.example`
- Removed evaluator API methods + `EvaluatorInfo` import from `api.ts`
- Removed evaluator re-export from `types/index.ts`
- Removed `evaluator_id` from `EvaluationConfig` (evaluation.ts) and `CreateSessionRequest.agent_config` (session.ts)
- Removed `EvaluatorSelector` component + `useEvaluatorStore` import + `selectedEvaluatorId` gating + `evaluator_id` config assignment + `resetSelection()` calls from all 4 evaluate pages
- Rewrote `Settings.tsx`: removed Evaluators tab, defaultValue→"rubrics", updated description
- Rewrote `Settings.test.tsx`: removed evaluator mock/assertions, updated tab count
- Fixed `ArenaComparison.test.tsx`: removed evaluator-selector mock, store mock, assertions
- Fixed `AgentEvaluation.test.tsx`: removed evaluator-selector mock, store mock
- Deleted `TestEvaluatorRegistryReload` class from `test_yaml_reload.py`, kept `TestProviderRegistryReload`
- Fixed `test_arena_evaluation_service.py`: patch target `create_evaluation_adapter` → `LiteLLMJudgeAdapter`

**ARCH-008** — Moved scored sessions migration to Alembic:
- Created Alembic revision `f25d781af937_migrate_scored_sessions_data.py`: `op.execute("UPDATE sessions SET status = 'completed' WHERE ...")`
- Deleted `_migrate_scored_sessions()` function and its lifespan call from `main.py`
- Lifespan now only has: logging config, auth warning, Alembic migrations, yield, shutdown log

**Files modified:**
- Modified: `backend/app/main.py`, `backend/app/models/__init__.py`, `backend/app/models/evaluation.py`, `backend/app/schemas/evaluation.py`, `backend/app/schemas/run.py`, `backend/app/api/v1/evaluations.py`, `backend/app/core/config.py`, `backend/pyproject.toml`, `.env.example`
- Modified: `backend/app/services/evaluation_service.py`, `backend/app/services/arena_evaluation_service.py`, `backend/app/services/rag_evaluation_service.py`
- Modified: `backend/tests/unit/test_run_schemas.py`, `backend/tests/unit/test_yaml_reload.py`, `backend/tests/unit/test_arena_evaluation_service.py`
- Modified: `frontend/src/App.tsx`, `frontend/src/App.test.tsx`, `frontend/src/components/layout/TopNav.tsx`, `frontend/src/services/api.ts`, `frontend/src/types/index.ts`, `frontend/src/types/evaluation.ts`, `frontend/src/types/session.ts`, `frontend/src/stores/evaluationStore.test.ts`
- Modified: `frontend/src/pages/QAEvaluation.tsx`, `frontend/src/pages/RAGEvaluation.tsx`, `frontend/src/pages/AgentEvaluation.tsx`, `frontend/src/pages/ArenaComparison.tsx`, `frontend/src/pages/Settings.tsx`, `frontend/src/pages/Settings.test.tsx`, `frontend/src/pages/AgentEvaluation.test.tsx`, `frontend/src/pages/ArenaComparison.test.tsx`
- Modified: `docs/docs/environments.md`
- Created: `backend/alembic/versions/346b00c58bbe_drop_environments_table_and_environment_.py`, `backend/alembic/versions/f25d781af937_migrate_scored_sessions_data.py`
- DELETED (backend): `backend/app/environments/` (3 files), `backend/app/api/v1/environments.py`, `backend/app/models/environment.py`, `backend/app/schemas/environment.py`, `backend/app/adapters/registry.py`, `backend/app/adapters/factory.py`, `backend/app/api/v1/evaluators.py`, `config/evaluators.yaml`, `backend/tests/unit/test_evaluator_registry.py`, `backend/tests/unit/test_eval_adapter_factory.py`, `backend/tests/unit/test_evaluator_config_files.py`
- DELETED (frontend): `frontend/src/pages/Environments.tsx`, `frontend/src/types/environment.ts`, `frontend/src/components/evaluation/EvaluatorSelector.tsx(+test)`, `frontend/src/components/settings/EvaluatorList.tsx(+test)`, `frontend/src/components/settings/EvaluatorDetail.tsx(+test)`, `frontend/src/stores/evaluatorStore.ts(+test)`, `frontend/src/types/evaluator.ts`
- DELETED (infra): `environments/compose/`, `environments/tmt/`, `environments/ansible/`, `environments/scenarios/`

Branch: `fix/review-phase1-simp001-simp002-arch008`

### Verification
- Backend pytest: 868 passed (was 915; -47 from deleted evaluator/env tests)
- Backend ruff check: 0 errors
- Backend ruff format: 211 files already formatted
- Frontend tests: 562 passed (was 607; -45 from deleted evaluator component/store tests + Settings adjustments)
- Frontend lint: 6 warnings (unchanged, not errors)
- Frontend build: succeeds
- Graph validator: green
- Fresh DB (`/tmp/es_verify_simp.db`): all migrations run, app boots, health check passes, no `environments`/`providers` tables, no startup migration logs
- OpenAPI spec: no `/environments` or `/evaluators` endpoints
- `grep -rn "evaluator" backend/app frontend/src --include="*.py" --include="*.ts" --include="*.tsx" -il` → only `litellm_judge.py` internals, `adapters/base.py` ABC
- No `environment_id` in backend app code
- No baseline regressions

### Graph/roadmap updates
- SIMP-001: status → done
- SIMP-002: status → done
- ARCH-008: status → done
- FE-005: status → done (superseded by SIMP-001)
- DOC-003: status → done (superseded by SIMP-001)
- SIMP-005: status → done (superseded by SIMP-002)
- BUG-018: status → done (conflict loser to SIMP-002, closed unimplemented)

### New issues discovered
None.

### Breaking changes
**SIMP-001**: All `/api/v1/environments` endpoints removed. `environment_id` field removed from evaluation create/response and run request schemas. `asyncssh` dependency removed.
**SIMP-002**: All `/api/v1/evaluators` endpoints removed. Evaluator selector no longer appears on evaluate pages — evaluations run directly with `LiteLLMJudgeAdapter`. Evaluators tab removed from Settings.
**ARCH-008**: No breaking changes (internal migration mechanism change).

### Handoff / next session should start with
Continue **Phase 1 — Structural decisions**:
1. **SEC-001** (M, high) — Secrets out of evaluation.config (env-var indirection, redaction). Top remaining priority.
2. **SIMP-004** (M, medium) — Delete clients/ SDK+CLI (closes INFRA-005)
3. **SIMP-006** (S, low) — Prune deps (rides the SIMP-001/002 deletions — asyncssh already removed)
4. **ARCH-001** (L, high) — Single eval runner (large; fold BUG-001/016/009/010/012/015)
5. **ARCH-006** (S, high) — Single session end (closes BUG-008)

SEC-001 is the clear next priority — credentials are currently readable via API and artifacts. SIMP-004/006 are quick deletion wins to batch with it.

---

## Session 4 — 2026-06-15 — claude-opus-4-6[1m]

### Baseline observed
- Backend tests: 917 passed
- Backend lint: 0 errors
- Backend format: 195 files already formatted
- Frontend tests: 607 passed
- Frontend lint: 6 warnings (not errors)
- Frontend build: succeeds
- Graph validator: green

### Scope chosen + why
**Phase 1 begins.** Two issues, S + M effort:

1. **INFRA-001** (S, critical) — Serve the SPA from the production image. The review's only
   critical issue: the Containerfile copies the frontend build to `/app/static/` but FastAPI
   never mounts it. Production UI is a 404. CI smoke test only checks `/api/v1/health`.
   Fix: add static file mounting + SPA fallback in `main.py`, extend CI smoke test.

2. **ARCH-002** (M, high, breaking) — Delete the dead DB provider store. Pure deletion:
   remove `models/provider.py`, `resolve_provider()`, the startup migration, and related tests.
   Add Alembic migration to drop the `providers` table. Closes CONS-007 (superseded),
   unblocks DUP-010, DATA-006, TEST-002.

Reasoning: INFRA-001 is #1 priority per ROADMAP (critical, first in Phase 1). ARCH-002 is
pure deletion with high downstream impact (unblocks 3 issues, closes 1). Both are dependency-free.
SEC-001 (the next roadmap item) is more complex (schema changes, data migration, breaking RAG
config) and benefits from landing after ARCH-002's provider cleanup. S + M fits one session.

### Changes

**INFRA-001** — Added production SPA serving to `backend/app/main.py`:
- Computes `_static = Path(__file__).resolve().parents[1] / "static"`, guarded by `is_dir()`.
- Mounts `/assets` via `StaticFiles` for hashed Vite assets.
- Registers catch-all `GET /{full_path:path}` route (last, so API/WS routes win) that serves
  existing files directly or falls back to `index.html` for client-side routes.
- Extended CI smoke test (`.github/workflows/ci.yml`) to verify `curl /` returns HTML and
  SPA deep link `/results` also returns HTML.
- Added 6 tests (`test_spa_serving.py`): root, deep route, nested deep route, direct file,
  hashed asset via mount, API route not caught by catch-all.

**ARCH-002** — Deleted the dead DB provider store:
- DELETED `backend/app/models/provider.py` (the unused ORM model).
- Removed `Provider` from `backend/app/models/__init__.py`.
- Deleted `resolve_provider()` and its dead imports (`select`, `AsyncSession`, `Provider`)
  from `backend/app/services/provider_utils.py`. Also removed now-unused `ProviderProfile` import.
- Deleted `_migrate_single_model_providers()` function and its lifespan call from `main.py`.
- Added Alembic migration `66b746a633ce_drop_providers_table.py` (`op.drop_table("providers")`
  with full `downgrade` to recreate the table).
- DELETED `backend/tests/unit/test_provider_model.py` (8 tests for the dead model).
- CONS-007 auto-closed (superseded): the `getattr()` pattern only existed in `resolve_provider`.

**Files modified:**
- Modified: `backend/app/main.py`, `backend/app/models/__init__.py`,
  `backend/app/services/provider_utils.py`, `.github/workflows/ci.yml`
- Created: `backend/tests/unit/test_spa_serving.py`,
  `backend/alembic/versions/66b746a633ce_drop_providers_table.py`
- DELETED: `backend/app/models/provider.py`, `backend/tests/unit/test_provider_model.py`

Branch: `fix/review-phase1-infra001-arch002`

### Verification
- Backend pytest: 915 passed (917 - 8 deleted + 6 added)
- Backend ruff check: 0 errors
- Backend ruff format: 195 files already formatted
- Frontend tests: 607 passed (unchanged)
- Frontend lint: 6 warnings (unchanged, not errors)
- Frontend build: succeeds
- Graph validator: green
- Fresh DB verification: `DATABASE_URL="sqlite+aiosqlite:////tmp/es_verify_arch002.db"` →
  all migrations run including `drop_providers_table`, app boots, health check passes,
  `sqlite3 .tables` confirms no `providers` table.
- `grep -rn "models.provider\|resolve_provider" backend/` → no hits (false positives only:
  `provider_id` parameter names and `test_resolve_provider_id_not_found` which tests
  `resolve_model_config`, not the deleted function).
- No "startup.migrated_single_model_providers" log line on fresh boot.
- No baseline regressions.

### Graph/roadmap updates
- INFRA-001: status → done
- ARCH-002: status → done
- CONS-007: status → done (superseded by ARCH-002)

### New issues discovered
None.

### Breaking changes
**ARCH-002**: The `providers` DB table is dropped. Pre-existing local DB rows are abandoned.
Users must re-create providers via Settings → Providers (config/providers.yaml). Acceptable
per project stage (no external consumers, internal tool).

### Handoff / next session should start with
Continue **Phase 1 — Structural decisions**, in priority order:
1. **SEC-001** (M, high) — Secrets out of evaluation.config (env-var indirection for auth_header, redaction pass)
2. **SIMP-001** (M, high) — Delete environments vertical (~900 lines, closes FE-005, DOC-003)
3. **SIMP-002** (M, high) — Delete evaluator machinery (~1,400 lines, closes SIMP-005, resolves BUG-018)
4. **ARCH-008** (S, medium) — Remove lifespan raw-SQL migrations (now only `_migrate_scored_sessions` remains)
5. **SIMP-004** (M, medium) — Delete clients/ SDK+CLI (closes INFRA-005)

SEC-001 is the top priority (credentials readable via API and artifacts). SIMP-001 and SIMP-002
are high-impact pure deletions. ARCH-008 is now simpler since `_migrate_single_model_providers`
was already deleted in this session.

---

## Session 3 — 2026-06-15 — claude-opus-4-6[1m]

### Baseline observed
- Backend tests: 915 passed
- Backend lint: 0 errors
- Backend format: 0 files to reformat
- Frontend tests: 606 passed
- Frontend lint: 6 warnings (not errors)
- Frontend build: succeeds
- Graph validator: green

### Scope chosen + why
Complete Phase 0 — batch of 10 remaining XS quick wins, all dependency-free:

1. **BUG-012** (XS) — RAG judge hardcodes threshold/temperature
2. **BUG-014** (XS) — Rubric generate/refine never pass API key
3. **BUG-015 + PERF-004** (XS pair) — Rerun stale artifacts + bulk delete
4. **SIMP-003** (XS) — Delete BuiltinHarness
5. **SIMP-007** (XS) — Delete examples/judges/ (+ DOC-004 auto-closes)
6. **API-001** (XS) — Fix rubrics pagination params (FE)
7. **DUP-001** (XS) — Consolidate _utcnow/_iso_now
8. **DATA-002** (XS) — Dataset.tags type mismatch
9. **DATA-004** (XS) — Legacy Column() for metadata
10. **INFRA-006** (XS) — Rewrite providers.yaml.example

Stretch (if time): DUP-005, PERF-002, INFRA-003, INFRA-004, CONS-001, CONS-006.

Reasoning: All are Phase 0 quick wins, highest-priority among remaining ready items.
Sessions 1-2 completed 11 items; this batch completes the core Phase 0 list.

### Changes

**SIMP-007** — Deleted `examples/judges/` directory (panel-judge.yaml, standard-judge.yaml).
DOC-004 auto-closes (superseded).

**SIMP-003** — Deleted `backend/app/harnesses/builtin.py`. Removed builtin branch from
`factory.py`. Updated `registry.py` default type from "builtin" to "subprocess". Updated
`base.py` docstring. Test `test_create_builtin_harness` → `test_create_builtin_type_raises`.

**DATA-002** — `models/dataset.py:20`: `Mapped[dict | None]` → `Mapped[list | None]`.

**DATA-004** — `models/dataset.py:36`: `Column("metadata", ...)` → `mapped_column("metadata", ...)`.
Removed unused `Column` import.

**DUP-001** — Exported `utcnow()` and `iso_now()` from `core/database.py`. Replaced 7 local
`_utcnow` definitions (6 model files + database.py) and 2 local `_iso_now` definitions
(agent_chat_service.py, websocket/chat.py) with imports. Also replaced 2 inline
`datetime.now(UTC)` calls in chat.py and agent_chat_service.py. Net: ~18 lines deleted,
single source of truth for timestamps.

**BUG-012** — Added `judge_config: JudgeConfigParams | None = None` parameter to `evaluate_rag`
in ABC (`adapters/base.py`) and implementation (`litellm_judge.py`). Uses
`judge_config.pass_threshold` for per-metric pass flags and `judge_config.temperature`
for the LLM call. Updated call site in `rag_evaluation_service.py` to pass `judge_params`.
+1 test (threshold=0.5, score=0.6 → passed=True, temperature=0.3 forwarded).

**BUG-014** — Added `api_key: str | None` parameter to `generate_rubric` and `refine_rubric`
in `rubric_service.py`. Added `_api_key_env_patch()` context manager that temporarily sets
`LITELLM_API_KEY` so rubric-kit's internal litellm calls pick it up. Updated call sites in
`rubrics.py` to pass `provider.api_key`. +1 test (captures env var during mock call).

**BUG-015 + PERF-004** — Added `_cleanup_artifacts()` helper in `evaluations.py` that deletes
artifact files from disk and artifact rows for an evaluation. Called from both `rerun_evaluation`
and `delete_evaluation`. Replaced row-by-row `db.delete(r)` loop with bulk
`delete(Result).where(...)`.

**API-001** — Changed `listRubrics` in `frontend/src/services/api.ts` from `offset`/`limit`
params to `page`/`page_size` to match backend endpoint signature.

**INFRA-006** — Rewrote `config/providers.yaml.example` with current field names
(`default_model` instead of `litellm_model`, removed `purpose`). Dropped redundant judge
entry. Added commented custom provider example.

**DUP-005** (stretch) — Extracted `_broadcast()` helper in `websocket/progress.py`.
Three public functions (`broadcast_progress`, `broadcast_log`, `broadcast_status`) now
delegate send/sweep logic. Also replaced `datetime.now(UTC).isoformat()` with `iso_now()`.
~45 lines removed. Updated test to patch `iso_now` instead of `datetime`.

**PERF-002** (stretch) — Added `MAX_LOGS = 500` cap to `evaluationStore.ts`. Log buffer
uses ring-buffer slice: `state.logs.slice(-(MAX_LOGS - 1))`. +1 FE test (push 600 logs →
length=500, first entry = Log 101).

**INFRA-003** (stretch) — Added `uv sync --quiet` and `npm install --silent` to `dev.sh`.
Made `Makefile` `dev:` target delegate to `./dev.sh` instead of duplicating the launcher.

**INFRA-004** (stretch) — Changed `docs-serve` and `docs-build` Makefile targets from
`cd docs && uv run mkdocs` to `cd backend && uv run mkdocs -f ../docs/mkdocs.yml`.

**Files modified/deleted:**
- DELETED: `examples/judges/panel-judge.yaml`, `examples/judges/standard-judge.yaml`
- DELETED: `backend/app/harnesses/builtin.py`
- Modified (backend): `app/harnesses/factory.py`, `app/harnesses/base.py`,
  `app/harnesses/registry.py`, `app/core/database.py`, `app/models/dataset.py`,
  `app/models/evaluation.py`, `app/models/session.py`, `app/models/rubric.py`,
  `app/models/environment.py`, `app/models/provider.py`, `app/websocket/chat.py`,
  `app/websocket/progress.py`, `app/services/agent_chat_service.py`,
  `app/services/rubric_service.py`, `app/adapters/base.py`,
  `app/adapters/litellm_judge.py`, `app/services/rag_evaluation_service.py`,
  `app/api/v1/evaluations.py`, `app/api/v1/rubrics.py`
- Modified (frontend): `src/services/api.ts`, `src/stores/evaluationStore.ts`,
  `src/stores/evaluationStore.test.ts`
- Modified (tests): `tests/unit/test_harness_factory.py`, `tests/unit/test_rag_judge.py`,
  `tests/unit/test_rubric_service.py`, `tests/unit/test_websocket_progress.py`
- Modified (infra): `Makefile`, `dev.sh`, `config/providers.yaml.example`

Branch: `fix/review-phase0-batch3`

### Verification
- Backend pytest: 917 passed (was 915, +2 new tests for BUG-012 and BUG-014)
- Backend ruff check: 0 errors
- Backend ruff format: 0 files to reformat
- Frontend tests: 607 passed (was 606, +1 new test for PERF-002)
- Frontend lint: 6 warnings (unchanged, not errors)
- Frontend build: succeeds
- Graph validator: green
- No regressions from baseline.

### Graph/roadmap updates
- BUG-012, BUG-014, BUG-015, PERF-004, SIMP-003, SIMP-007, API-001, DUP-001, DUP-005,
  DATA-002, DATA-004, INFRA-003, INFRA-004, INFRA-006, PERF-002: status → done
- DOC-004: status → done (superseded by SIMP-007)
- Phase 0 is now **complete** except for CONS-001 (S) and CONS-006 (S)

### New issues discovered
None.

### Breaking changes
None. All fixes are internal behavioral corrections — no API or schema changes.

### Handoff / next session should start with
Phase 0 has 2 remaining S-sized items (CONS-001, CONS-006) — can be done as warm-up.

Then begin **Phase 1 — Structural decisions**, in priority order:
1. **INFRA-001** (S, critical) — Serve the SPA from the production image
2. **SEC-001** (M, high) — Secrets out of evaluation.config
3. **ARCH-002** (M, high) — Delete DB provider store (closes CONS-007)
4. **SIMP-001** (M, high) — Delete environments vertical (closes FE-005, DOC-003)
5. **SIMP-002** (M, high) — Delete evaluator machinery (closes SIMP-005, resolves BUG-018)

INFRA-001 is the review's only critical issue and is a small fix — start there.

### Addendum: CONS-001 + CONS-006

**CONS-001** — `.env.example` drift fix:
- Renamed `LITELLM_MODEL` → `DEFAULT_MODEL` with updated comment
- Removed `LITELLM_API_BASE` (no corresponding setting; providers own api_base)
- Added missing settings: `ARTIFACTS_DIR`, `RUN_TIMEOUT_DEFAULT`, `RUN_TIMEOUT_MAX`
- Deleted "Planned / Future" section (TESTING_FARM_*, MLFLOW_*, BACKEND_HOST/PORT — nothing reads them)
- Fixed docstring in `provider_utils.py:50` (LITELLM_MODEL → DEFAULT_MODEL)

**CONS-006** — Log event naming cleanup (~15 renames to `domain.action` format):
- `registry_base.py`: `skipping_non_dict_entry` → `registry.entry_skipped`, `config_file_deleted` → `registry.config_deleted`, `config_file_changed` → `registry.config_changed`, `config_write_failed` → `registry.write_failed`
- `evaluators.py`: `config_file_uploaded` → `evaluator_config.uploaded`, `config_file_deleted` → `evaluator_config.deleted`
- `providers.py`: `"failed to fetch models from provider"` → `provider.models_fetch_failed`
- `adapters/registry.py`: `skipping_evaluator_missing_fields` → `evaluator.entry_missing_fields`, `adapter_outside_allowed_namespaces` → `evaluator.adapter_outside_namespace`, `adapter_not_importable` → `evaluator.adapter_not_importable`
- `main.py`: prose events → `app.startup`, `app.shutdown`, `app.auth_disabled`, `startup.migrated_*`

Files modified: `.env.example`, `backend/app/services/provider_utils.py`, `backend/app/main.py`, `backend/app/api/v1/providers.py`, `backend/app/api/v1/evaluators.py`, `backend/app/core/registry_base.py`, `backend/app/adapters/registry.py`

**Phase 0 is now fully complete** (27 issues implemented + 2 superseded = 29 resolved).

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

| ID | Session | Notes |
|----|---------|-------|
| INFRA-007 | 1 | + mako template fix to prevent regressions |
| INFRA-008 | 1 | Actual error count was ~30+, not 5 as documented |
| BUG-003 | 2 | Base class try/except wraps all registries |
| BUG-004 | 2 | parents[3] path fix |
| BUG-005 | 2 | JSON-escaped template substitution |
| BUG-007 | 2 | single_model passed through + always serialized |
| BUG-009 | 2 | RAG adapter close() in finally |
| BUG-010 | 2 | sanitize_error_for_client in all 3 services |
| BUG-017 | 2 | extract_json_path error wrapping |
| INFRA-002 | 2 | Alembic migrations at startup |
| BUG-006 | 2 | Superseded by INFRA-002 |
| SIMP-007 | 3 | Deleted examples/judges/ |
| SIMP-003 | 3 | Deleted BuiltinHarness |
| DATA-002 | 3 | tags: dict → list |
| DATA-004 | 3 | Column() → mapped_column() |
| DUP-001 | 3 | Consolidated _utcnow/_iso_now into database.py |
| BUG-012 | 3 | RAG judge uses configured threshold/temperature |
| BUG-014 | 3 | API key threaded into rubric generate/refine |
| BUG-015 | 3 | Rerun cleans up stale artifacts |
| PERF-004 | 3 | Bulk delete results on rerun |
| API-001 | 3 | FE rubrics pagination offset/limit → page/page_size |
| INFRA-006 | 3 | Rewrote providers.yaml.example with current fields |
| DUP-005 | 3 | Extracted _broadcast() helper in progress.py |
| PERF-002 | 3 | FE log buffer capped at 500 |
| INFRA-003 | 3 | Makefile dev: delegates to dev.sh |
| INFRA-004 | 3 | docs-serve/build targets use backend uv env |
| DOC-004 | 3 | Superseded by SIMP-007 |
| CONS-001 | 3 | .env.example reconciled with Settings |
| CONS-006 | 3 | ~15 log events renamed to domain.action |
| INFRA-001 | 4 | SPA serving + CI smoke extension |
| ARCH-002 | 4 | Deleted DB provider store + migration |
| CONS-007 | 4 | Superseded by ARCH-002 |
| SIMP-001 | 5 | Deleted environments vertical (~900 lines + 4 dirs) |
| SIMP-002 | 5 | Deleted evaluator machinery (~1,400 lines); direct LiteLLMJudgeAdapter |
| ARCH-008 | 5 | _migrate_scored_sessions → Alembic; lifespan clean |
| FE-005 | 5 | Superseded by SIMP-001 |
| DOC-003 | 5 | Superseded by SIMP-001 |
| SIMP-005 | 5 | Superseded by SIMP-002 |
| BUG-018 | 5 | Conflict loser to SIMP-002 (closed unimplemented) |

**Total: 39 issues done** (32 direct + 7 superseded/conflict-closed) out of 94.

---

## Next recommended issue(s)

Phase 1 structural decisions — see Session 5 handoff above.
