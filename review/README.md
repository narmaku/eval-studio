# eval-studio — Deep Quality Review

Reviewed at commit `ffc4b27` (branch `main`), 2026-06-11. **94 issues** across 13 categories, cross-linked into a dependency/supersession graph, with a phased execution roadmap and a target architecture. No source files outside `review/` were modified. Toolchain was executed at the end of the review: backend 900 tests pass, frontend 606 tests pass — but **lint, `npm run build`, fresh-database startup, and `make docs-build` all fail on main today** (INFRA-007, INFRA-008, BUG-006-confirmed, INFRA-004-confirmed).

## Executive summary (1 page)

**The five structural decisions that matter most:**

1. **Make the shipped product actually work end-to-end.** The production image cannot currently be built at all (`npm run build` fails with type errors — INFRA-008), would not serve the UI it contains even if built (INFRA-001, the review's only *critical*), and no startup path creates the database schema (INFRA-002) — a fresh start **crashes, verified**: `sqlite3.OperationalError: no such table: sessions → Application startup failed` (BUG-006). All fixes are small; all are invisible to the current CI.
2. **Collapse the three copies of the evaluation engine into one** (ARCH-001). QA/Arena/RAG are ~85% identical 330-line scripts; most of the review's behavioral bugs (dead error guards, inconsistent thresholds, leaked clients, stale artifacts) are divergences between the copies. One runner + three small mode plugins deletes ~600 lines and gives lifecycle invariants a single home.
3. **Delete the speculative machinery.** The environments vertical is 100% stubs and 501s (SIMP-001); the pluggable-evaluator registry guards a dispatch that never fires — the evaluator users select in the UI is consulted by nothing (BUG-018/SIMP-002); the clients/ SDK is an untested third mirror of the API (SIMP-004); the DB provider table is dead alongside the live YAML registry (ARCH-002). Roughly **5,000+ lines** can be removed while making the product more honest, plus 21 of 22 alembic revisions (DATA-006).
4. **Give the contracts an owner.** FE types, backend schemas, and the WS chat protocol are hand-mirrored and demonstrably drifted (broken rubric pagination API-001, undefined chat message ids ARCH-003/FE-006, phantom `cancelled` status API-004). Generate FE types from OpenAPI (ARCH-004), type the WS envelopes in Pydantic (ARCH-003), and decide the cancellation story (API-004).
5. **Declare the trust model and stop leaking secrets.** Auth is off by default, the FE can't authenticate, WS endpoints never check anything, dev servers bind 0.0.0.0, and RAG bearer tokens/connection strings are stored in `evaluations.config`, returned by list endpoints, and baked into downloadable artifacts (SEC-001..005).

**The single biggest risk in the codebase today:** SEC-001 — live credentials (RAG `auth_header` tokens, DB connection strings) flowing through `evaluation.config` into API responses and downloadable artifacts, in a system that is network-reachable by default with auth off. One shared `config.json` artifact equals leaked credentials.

**Counts:** 94 issues — 1 critical, 15 high, 38 medium, 36 low, 4 trivial. 11 are pure graph records (closed automatically by a superseding fix); 2 more close via conflict resolution. **~81 issues need direct implementation; estimated total effort ≈ 30–35 focused engineer-days**, of which Phase 0 (25 quick wins) is ~2 days and net-deletes code.

**State of health, honestly:** the codebase has real strengths — consistent async SQLAlchemy 2.0, RFC 7807 error envelope with sanitization, subprocess allowlisting, structlog with correlation ids, and a sizeable, mostly meaningful test suite. The dominant disease is *unfinished verticals shipped as if finished* (environments, evaluator selection, rubrics-that-score-nothing, auth-nobody-can-use) and *copy-paste growth* in the engine. Both are highly fixable at this stage.

## How to navigate

```
review/
├── README.md                ← you are here
├── 00-meta/                 ← methodology, environment/toolchain record, repo inventory,
│                               honest as-is architecture
├── 01-architecture …13-docs ← one file per issue; YAML frontmatter carries the graph
└── 99-synthesis/
    ├── INDEX.md             ← master table of all 92 issues + statistics
    ├── GRAPH.md             ← mermaid diagram, cascade table, conflict resolutions
    ├── ROADMAP.md           ← phases 0–4 with ordering rationale and checkpoints
    ├── TARGET-ARCHITECTURE.md ← the destination all structural issues align to
    ├── QUICK-WINS.md        ← the ≤1h, zero-dependency Phase-0 batch
    └── check_graph.py       ← validates edge symmetry / dangling refs / cycles
```

**Suggested reading order:** this page → `00-meta/architecture-current.md` → `TARGET-ARCHITECTURE.md` → `ROADMAP.md` → issues as you implement, via `INDEX.md`.

**Working the issues:** before implementing anything, run `check_graph.py`; before picking an issue, check its `superseded_by` (it may already be moot) and its `depends_on` (it may need a structural issue first). Issue IDs are stable — never renumber.

**Caveats:** a command-safety tooling outage blocked test/linter/build execution for most of the review; the outage lifted before completion and the full toolchain was then run (`00-meta/environment.md` records every result verbatim). BUG-006 and INFRA-004 were empirically confirmed and upgraded to `confidence: high`; INFRA-007/008 were filed from the failures. The only remaining `confidence: medium` items are judgment-bearing (DATA-005, TEST-003) or timing-dependent (BUG-016). All file:line citations were made against `ffc4b27` and verified by reading the code.
