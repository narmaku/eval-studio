# Methodology

## Process actually followed

**Phase A — Inventory.** Full file listing (466 files); read all root infra (Makefile, dev.sh, both compose files, Containerfile, nginx.conf, .env.example, CI workflows), both pyprojects + package.json, CLAUDE.md/README/CONTRIBUTING-adjacent docs. Wrote `inventory.md`, `architecture-current.md`, `environment.md`.

**Phase B — Category passes (read-exhaustive on the backend, prioritized on the frontend).**
- Backend: read **every** file in `backend/app/` (102 source files: main, core/*, models/*, all 15 routers, all 11 services, adapters/*, agent_backends/*, rag_backends/*, harnesses/* incl. parsers, mcp/*, environments/*, websocket/*, key schemas) plus `tests/conftest.py`, `alembic/env.py`, representative tests (`test_provider_utils.py` in full; others via targeted greps).
- Frontend: read `services/api.ts`, `App.tsx`, `main`-adjacent files, stores (evaluationStore, sessionStore, resultStore, notificationStore in full; others via greps), `types/session.ts`, `QAEvaluation.tsx`, `EvaluationProgress.tsx`; surveyed remaining pages/components via line counts and targeted greps (dependency usage, duplicate patterns). **Not read line-by-line:** most presentational components and their tests, chart components, shadcn ui/ primitives — judged low-risk; noted here as the honest gap.
- clients/: pyproject + `client.py` (first 120 lines) + structure; judged at package level (the SIMP-004 finding does not require line-level reading).
- config/, examples/, environments/, docs/: read in full (small).
- Cross-referencing greps for every "X is unused/never called" claim (`resolve_provider`, `evaluator_id`, `supports_mode`, `StaticFiles`, `create_all`, `asyncssh`, dependency imports, etc.). Every such claim in an issue cites the grep.

**Phase C — Target synthesis.** `TARGET-ARCHITECTURE.md` written after all categories; structural issues were written with it in mind and re-checked against it (decision points cross-referenced in both directions).

**Phase D — Graph pass.** All relationship fields assigned at write time; five asymmetries found and corrected in a dedicated pass (ARCH-002/ARCH-003/SIMP-002/SIMP-003/API-004 `blocks` lists). `check_graph.py` written; execution blocked by the tooling outage (below), so a **manual full-edge audit** was performed and is recorded in GRAPH.md. Run the script before acting on the review.

**Phase E — Synthesis docs.** INDEX (94 rows + stats), ROADMAP (5 phases + checkpoints + conflict resolutions), QUICK-WINS (25 items), README (executive summary). (Counts include the two post-toolchain INFRA additions.)

**Phase F — Self-audit.** See bottom of this file.

## Toolchain execution record

A command-safety classifier outage in the review agent's harness blocked all non-read-only shell commands for most of the session (pure read-only grep/wc/find worked); the static passes therefore carried the review, with execution-dependent findings filed at `confidence: medium`. **The outage lifted at the end of the session and the full toolchain was executed** — results verbatim in `00-meta/environment.md`. Outcomes:
- Backend: 900 tests pass; ruff FAILS (5 errors, one migration file) → **INFRA-007 filed**.
- Frontend: 606 tests pass; eslint clean (6 warnings); `npm run build` FAILS (5 tsc errors in test fixtures → container image cannot build) → **INFRA-008 filed**.
- BUG-006 reproduced exactly as predicted (`no such table: sessions` → startup abort) → upgraded to `confidence: high`.
- INFRA-004 reproduced (`Failed to spawn: mkdocs`) → upgraded to `confidence: high`.
- `check_graph.py` executed: graph valid (94 issues, 27 hard edges, 11 superseded, no violations) — agreeing with the earlier manual audit.
- `pip-audit`/`npm audit` not run; dependency-CVE review remains the one open gap.

## Checklist coverage — clean bills of health

Dimensions investigated that produced **no issue** (checked, found acceptable):
- **SQLAlchemy 2.0 idiom consistency** — uniformly modern (`select()`, `Mapped`, async sessions); the single deviation is DATA-004.
- **Mock-theater / tautological tests** — sampled unit tests (provider_utils, conftest patterns, judge tests per grep) assert real behavior, not mock echoes; no tautology pattern found worth filing. (Dead-code-pinning tests are TEST-002 — a different defect.)
- **Brittle tests (order/time/network dependence)** — conftest uses in-memory DB + isolated registries; no network-touching tests found (LLM calls mocked); not exhaustively proven without a run, but structurally sound.
- **Upload size/type limits** — dataset import enforces per-file/aggregate/count caps and binary detection (`dataset_import.py:48-101`); evaluator config files capped at 10 MB; artifact preview capped at 1 MB with XSS-conscious content-type policy (`artifacts.py:19-30`) — notably good.
- **Path traversal defenses** — artifact storage (`artifact_service.py:13-75`) and evaluator config files (`evaluators.py:102-126`) both validate correctly; checked against `..`, separators, resolution escapes.
- **CORS configuration** — explicit origin list, not `*` with credentials (`main.py:82-88`); fine.
- **MCP JSON-RPC client** — lifecycle, timeouts, stderr draining, allowlisting all sound (`mcp/client.py`); only the manager-level reuse bug (BUG-002) was found.
- **React hook hygiene** — no stale-closure or missing-cleanup defects found in the files read (effects clean up WS connections; `getState()` used where closures would go stale); list keys are fine except as caused by FE-006.
- **Frontend bundle weight** — heavy deps (recharts, jspdf+html2canvas) are all genuinely used (PDF export, charts); only the single-use form trio was actionable (CONS-008).
- **Rate limiter** (`core/rate_limiter.py`) — correct sliding-window implementation with sensible lock discipline; no issue.
- **Artifact atomic writes** — temp-file + rename done correctly (`artifact_service.py:115-128`).

## Known limitations of this review

1. Dynamic verification gap (toolchain outage) — every issue's Verification section compensates with exact commands for the implementer.
2. Frontend presentational layer and most FE test files not read line-by-line (see Phase B note) — duplication beyond FE-004/CONS-008 may exist there; expected impact low.
3. `clients/` reviewed at architecture level, not line level (its recommended disposition is deletion; line-level findings would be moot).
4. Dependency CVEs not audited.
5. Git history was consulted only via recent commit subjects; archaeology (e.g., when the provider rename happened) is inferred from migration names.

## Phase F — Self-audit record

Ten issues sampled (stratified across categories, randomized within): ARCH-002, DUP-006, CONS-001, BUG-005, BUG-013, SEC-001, SIMP-001, DATA-005, FE-001, INFRA-006. For each, three checks: (a) citations resolve to real lines, (b) fix spec implementable without re-deriving the analysis, (c) relationships bidirectional.

- **Citations:** re-verified by re-reading the cited ranges during the audit pass — all resolve. Two off-by-a-few line references were corrected during writing (BUG-007's constructor range; SEC-001's factory range); the audit found no remaining mismatches in the sample.
- **Implementability:** each sampled spec names exact files, functions, and before→after behavior; DATA-005 and SEC-001 include migration/sweep steps; judged implementable. DATA-005 flagged (correctly) as `confidence: medium` since it embeds a product decision.
- **Relationships:** sample's edges all bidirectional after the Phase-D fixes; the audit re-confirmed ARCH-002↔{DATA-006, DUP-010, TEST-002, CONS-007} and SIMP-001↔{FE-005, DOC-003} specifically.
- **Systemic check from audit findings:** the Phase-D asymmetry sweep (five fixes) was itself triggered by this audit pattern applied early; a final whole-graph manual pass found no further asymmetries. `check_graph.py` remains the mechanical arbiter — run it first.
