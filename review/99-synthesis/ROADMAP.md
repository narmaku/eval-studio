# Execution Roadmap

Derived by topological sort of `depends_on` with conflicts resolved per the recommendations below. Each phase ends with a checkpoint of runnable verifications. Superseded issues are never implemented — they close when their superseder lands.

## Conflict resolutions (decisions of record)

| Conflict | Winner | Loser disposition |
|---|---|---|
| SIMP-002 vs BUG-018 | **SIMP-002** (delete evaluator machinery) | BUG-018 closes unimplemented; revisit only if a second evaluator integration is concretely scheduled — then implement BUG-018 *instead* and keep the machinery |
| SIMP-004 vs INFRA-005 | **SIMP-004** (delete clients/) | INFRA-005 closes unimplemented |

Decision points embedded in issues (locked by TARGET-ARCHITECTURE.md): API-004 → option A (implement cancellation); CONS-008 → hand-rolled forms; CONS-004 → keep paginated/bare split as written rule.

---

## Phase 0 — Quick wins (1 PR, ~2 days)

Everything in `QUICK-WINS.md` (25 items): **INFRA-008 first** (un-breaks `npm run build`/container builds), INFRA-007 (un-breaks lint), then BUG-003/004/005/007/009/010/012/014/015/017, PERF-002/004, INFRA-003/004/006, CONS-001/006, DOC-001-interim, DOC-002-urls, DUP-001/005, DATA-002/004, API-001, SIMP-003/007.

**Why first:** all are dependency-free, none breaking, several are live user-facing failures (harness discovery, custom providers, stale examples). Landing them also de-noises later diffs.

**Checkpoint:** `uv run pytest`, `uv run ruff check .`, `npm test -- --run`, **and `npm run build`** green (the latter two are red on main today — INFRA-007/008); `cp config/providers.yaml.example config/providers.yaml` produces working providers; repo-root `config/harnesses.yaml` is discovered; a custom provider survives a question containing quotes.

---

## Phase 1 — Structural decisions (the supersession sources)

Order within phase (each unblocks the next group):

1. **INFRA-001** (serve the SPA) + **INFRA-002** (migrations at startup) — make the product deployable; closes BUG-006. Promoted ahead of everything because they're independent of all consolidations and currently the deepest breakage. **Critical SEC/BUG promotion note:** these are the Phase-3-class items promoted into Phase 1 per the severity rule; SEC-001 is additionally promoted into Phase 1 (below) because it's exposure, not restructuring-dependent.
2. **SEC-001** (secrets out of evaluation.config) with **SEC-004 + SEC-005** (trust model + posture + bind defaults; SEC-002 WS auth and SEC-003 identifier validation ride the same PR; PERF-003 optional rider).
3. **ARCH-002** (delete DB provider store) → closes CONS-007; then **ARCH-008** (lifespan migrations → Alembic).
4. **SIMP-001** (delete environments vertical) → closes FE-005, DOC-003; **SIMP-002** (delete evaluator machinery) → closes SIMP-005, resolves BUG-018; **SIMP-004** (delete clients/) → resolves INFRA-005; **SIMP-006** (dep pruning rides the deletions).
5. **ARCH-001** (single eval runner) — fold in BUG-001, BUG-016, and re-home the Phase-0 point fixes (BUG-009/010/012/015 locations); closes DUP-003, DUP-004.
6. **ARCH-006** (single session end) → closes BUG-008; then **FE-003**.
7. **ARCH-003** (typed WS protocol) → closes FE-006; **API-002** verification rides it.
8. **API-004 option A** (real cancellation) → unblocks FE-002.

**Expected breaking changes:** providers DB rows abandoned (ARCH-002); environments API/UI removed (SIMP-001); evaluator selection removed from UI (SIMP-002); clients/ gone (SIMP-004); WS envelope gains message_id (ARCH-003); RAG config shape changes for secrets (SEC-001).

**Checkpoint — after Phase 1 the following must be true:**
- `rm -f backend/eval_studio.db* && make dev` → app boots, UI loads, a QA evaluation runs end-to-end. (Verifies INFRA-002, ARCH-001.)
- `make docker-build && docker run -p 8000:8000 eval-studio:latest` → browser UI at `:8000`, deep link `/results` works. (INFRA-001.)
- `GET /api/v1/evaluations` responses and `config.json` artifacts contain no token/secret material for a RAG eval configured via env indirection. (SEC-001.)
- `grep -rn "resolve_provider\|models.provider\|environments\|evaluator_registry" backend/app` → no live hits. (Deletions.)
- Agent chat: messages have stable ids; cancel button cancels (server status `cancelled`).
- `python3 review/99-synthesis/check_graph.py` → closed issues marked; graph still valid.

---

## Phase 2 — Consolidation on the stable structure

Order: **DUP-002 → ARCH-005 → TEST-001** (registry path/Settings/test seam — a chain); **DUP-010** (after ARCH-002); **DUP-006 + BUG-013 + BUG-011** (judge call helper + proxy mechanism, one PR); **DUP-007 + DUP-011** (dataset import); **DUP-008**, **DUP-009 + CONS-004**, **DUP-012**; **ARCH-007** (chat loop decomposition + BUG-002 if not already point-fixed — BUG-002 may be promoted to Phase 0/1 if MCP usage is active daily); **FE-001** (replay buffer + run endpoint), **FE-004**, **CONS-008**; **CONS-002** (enums, after API-004 settled status truth); **CONS-003**, **CONS-005**.

**Why this order:** consolidations follow the structural deletions so they never touch code that's about to disappear; same-file work is batched (see GRAPH.md batching notes).

**Checkpoint:** `grep -c "_resolve_config_path" backend/app` = 1; provider round-trip test green (DUP-010); judge calls honor proxy under concurrency test (BUG-011/013); evaluate pages ≤ ~150 lines each (FE-004); zero raw status literals outside enums/tests (CONS-002).

---

## Phase 3 — Remaining correctness & safety

**DATA-001** (FKs, post-SIMP-001), **DATA-003** (tz columns), **DATA-005** (rubric/judge consolidation — the largest remaining feature-completing item; includes API-005), **PERF-001** (drop selectin), then **DATA-006** (squash the migration chain last, absorbing all schema deltas).

Anything from BUG-011/BUG-002 not yet landed completes here.

**Checkpoint:** rubric built in the UI demonstrably changes judge scoring breakdown (DATA-005); evaluation list latency flat vs seeded 50×200 dataset (PERF-001); fresh DB builds via a single migration (DATA-006); deleting a referenced dataset returns 409 (DATA-001).

---

## Phase 4 — Tests & docs against the final shape

**TEST-002** (delete dead-code tests — tranches unlocked through Phases 1), **TEST-003** (boot test, lifecycle contract, WS conformance snapshot, deep smoke), **ARCH-004** (type generation + CI drift gate; closes API-003), then the documentation rewrite: **DOC-001** (full CLAUDE.md rewrite), **DOC-002** (setup docs), remaining **DOC-003** residue (adapters.md), README sweep.

**Why last:** tests target the final structure (per review ground rules); docs describe the end state once.

**Checkpoint:** CI green including new jobs (type-drift gate, deep smoke, boot test); CLAUDE.md path-checklist script passes; a new contributor following getting-started succeeds on a clean machine without tribal knowledge.

---

## Issue → phase assignment summary

| Phase | Issues |
|---|---|
| 0 | QUICK-WINS list (25 items incl. INFRA-007/008 and interim DOC patches) |
| 1 | INFRA-001, INFRA-002, SEC-001..005, ARCH-002, ARCH-008, SIMP-001, SIMP-002, SIMP-004, SIMP-006, ARCH-001, BUG-001, BUG-016, ARCH-006, FE-003, ARCH-003, API-002, API-004, FE-002, PERF-003 |
| 2 | DUP-002, ARCH-005, TEST-001, DUP-010, DUP-006, BUG-011, BUG-013, BUG-002, DUP-007, DUP-011, DUP-008, DUP-009, CONS-004, DUP-012, ARCH-007, FE-001, FE-004, CONS-008, CONS-002, CONS-003, CONS-005 |
| 3 | DATA-001, DATA-003, DATA-005, API-005, PERF-001, DATA-006 |
| 4 | TEST-002, TEST-003, ARCH-004, DOC-001, DOC-002, DOC-003-residue |
| auto-close | DUP-003, DUP-004, CONS-007, BUG-006, BUG-008, SIMP-005, API-003, FE-005, FE-006, DOC-004 (+ BUG-018, INFRA-005 via conflict resolution) |
