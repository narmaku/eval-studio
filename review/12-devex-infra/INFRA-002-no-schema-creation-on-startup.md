---
id: INFRA-002
title: No startup path creates or migrates the database schema; first run requires an undocumented manual alembic step
category: devex-infra
severity: high
effort: S
confidence: high
breaking: false
status: open
depends_on: []
blocks: [TEST-003, DOC-002]
supersedes: [BUG-006]
superseded_by: []
conflicts_with: []
related: [ARCH-008, DATA-006, INFRA-001]
child_of: null
affected_paths:
  - backend/app/main.py
  - Makefile
  - dev.sh
  - Containerfile
  - docs/docs/getting-started.md
---

## Problem
Every launcher (make dev, dev.sh, both compose files, the production image CMD) starts uvicorn directly; nothing runs `alembic upgrade head`, and the app never calls `create_all`. The documented quick starts therefore produce a tableless database, which the lifespan's raw UPDATEs (ARCH-008) then hit immediately. The only mention of the migration command in the entire repo is one line in CLAUDE.md.

## Evidence
- `grep -rn "create_all\|alembic upgrade" backend/app Makefile dev.sh Containerfile backend/Dockerfile.dev .github docker-compose*.yml` → zero startup hits.
- Quick starts without the step: `docs/docs/getting-started.md:19-49`, `README.md:38-47`.
- `.env.example:22-23`: "The database file is created automatically on first run" (file yes, schema no).
- Crash mechanics: BUG-006.

## Impact
Broken first-run experience for every contributor and deployment; combined with INFRA-001, the production image fails on both of its two jobs (serve UI, answer API).

## Root cause
Everyone with a working checkout ran alembic once long ago; the path for the next person was never built or documented.

## Proposed fix (specification)
Run migrations automatically at startup (single-process SQLite makes this safe):
1. In `main.py` lifespan, before anything touches the DB:
   ```python
   def _run_migrations() -> None:
       from alembic import command
       from alembic.config import Config
       cfg = Config(str(Path(__file__).resolve().parents[1] / "alembic.ini"))
       cfg.set_main_option("script_location", str(Path(__file__).resolve().parents[1] / "alembic"))
       command.upgrade(cfg, "head")

   await asyncio.to_thread(_run_migrations)
   ```
   (alembic's env.py uses `asyncio.run`; running it in a worker thread avoids nested-loop conflict — verify with the existing async env.py, `backend/alembic/env.py:58-60`; if it conflicts, switch env.py to detect a running loop or use `command.upgrade` offline mode.)
2. Guard for tests: skip when `settings.database_url` is the in-memory test URL or behind a `RUN_MIGRATIONS_ON_STARTUP` setting defaulting true (conftest already creates tables itself, `tests/conftest.py:29-36`).
3. Document the manual command anyway in getting-started (for non-default DB paths) — DOC-002.
4. Multi-worker note: if uvicorn workers >1 ever happens, move the call to a container entrypoint script instead; record this constraint as a comment.

## Alternatives considered
1. Entrypoint shell script in the image (`alembic upgrade && uvicorn`) — fine for prod but doesn't fix `make dev`/`dev.sh`; the lifespan hook fixes all launchers at once.
2. `create_all` on startup — rejected: bypasses/duplicates Alembic and diverges schema from migrations.

## Verification
- `rm -f backend/eval_studio.db*; make dev` → backend starts, /health 200, tables exist (BUG-006's repro now passes).
- Fresh container run (CI smoke) green without preexisting volume.
- Second boot is a no-op (idempotent; startup time unchanged within noise).

## Relationship notes
- `supersedes: BUG-006` — the crash symptom is eliminated by automatic migration; closes with this.
- `blocks: TEST-003` (boot test targets this hook) and `DOC-002` (docs describe the final behavior).
- `related: ARCH-008` — its alembic-ified data migration rides the same startup hook; `DATA-006` — squashed chain makes the startup upgrade fast and clean.
