# Environment & Execution Record

## Review environment

- Host: Linux 6.19.7-200.fc43 (Fedora 43, immutable/ostree layout: repo at `/var/home/narmaku/development/eval-studio`).
- Review date: 2026-06-11. Branch `main`, commit `ffc4b27`, clean working tree (apart from this `review/` directory).
- Python 3.12.11 (uv-managed), Node 22 toolchain via npm.

## Tooling outage caveat

For most of the session the agent harness's command-safety classifier was unavailable, blocking all non-read-only shell commands; pure read-only commands (grep/wc/find) kept working, so the category passes proceeded on static evidence. The outage lifted near the end of the session and the full toolchain was then executed. Issues whose proof required execution were originally filed at `confidence: medium` and have been upgraded with verbatim evidence (BUG-006, INFRA-004); two new issues were filed from toolchain failures (INFRA-007, INFRA-008).

## Execution results (verbatim, post-outage)

| Action | Result |
|--------|--------|
| `python3 review/99-synthesis/check_graph.py` | **OK** — `issues: 94` (92 at first run; 94 after INFRA-007/008 were added and the script re-run), `hard edges: 27`, `superseded: 11`, `graph OK: no dangling refs, symmetric edges, no depends_on cycles` |
| `cd backend && uv sync --all-extras && uv run pytest -q` | **900 passed**, 10 warnings, 18.42s. Warnings include `PytestUnhandledThreadExceptionWarning: RuntimeError: Event loop is closed` from an aiosqlite worker thread during teardown (test-infra noise; not filed as an issue — single occurrence class, no test impact) |
| `uv run ruff check .` | **FAIL — 5 errors** (UP035, I001, UP007 ×3), all in `alembic/versions/1307fd3f3b27_add_single_model_to_providers.py`, all auto-fixable → **INFRA-007** |
| `uv run ruff format --check .` | **FAIL** — same file would be reformatted (195 others clean) → **INFRA-007** |
| `cd frontend && npm install && npm test -- --run` | **606 passed** in 57 files, 17.69s |
| `npm run lint` | **0 errors, 6 warnings** (`react-hooks/incompatible-library` re @tanstack/react-table usage) — warnings only, not filed |
| `npm run build` (`tsc -b && vite build`) | **FAIL — 5 type errors** in `evaluationStore.test.ts` (×2: fixtures missing `average_score`/`pass_rate`), `providerStore.test.ts` (×1: null vs string), `resultStore.test.ts` (×2: possibly-undefined) → **INFRA-008** (production image cannot build) |
| Fresh-DB startup (`DATABASE_URL=…fresh… uvicorn app.main:app`) | **CRASH** — `sqlite3.OperationalError: no such table: sessions` → `Application startup failed. Exiting.` → **BUG-006 confirmed**, upgraded to confidence: high |
| `make docs-build` | **FAIL** — `error: Failed to spawn: mkdocs — No such file or directory` → **INFRA-004 confirmed**, upgraded to confidence: high |
| `pip-audit` / `npm audit` | not run (network policy uncertain) — remains an open gap |
| Container build / compose up | not run directly; the docker build is provably broken anyway at the frontend stage (INFRA-008) |

## Summary

Dynamic verification confirmed the review's two riskiest static claims (fresh-DB startup crash; broken docs target) and surfaced two defects static reading could not see (lint red on main; production build red on main). Both test suites pass, which matches the review's assessment that test *quality* is decent while CI *coverage of the build/deploy path* is the gap (TEST-003, INFRA-008).
