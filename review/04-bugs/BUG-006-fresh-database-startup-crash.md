---
id: BUG-006
title: Backend startup crashes on a fresh database (lifespan UPDATEs run before any schema exists) — CONFIRMED
category: bugs
severity: high
effort: S
confidence: high
breaking: false
status: done (superseded by INFRA-002)
depends_on: []
blocks: []
supersedes: []
superseded_by: [INFRA-002]
conflicts_with: []
related: [ARCH-008]
child_of: INFRA-002
affected_paths:
  - backend/app/main.py
  - backend/app/core/database.py
---

## Problem
Nothing in any startup path creates the database schema (no `Base.metadata.create_all`, no `alembic upgrade` in Makefile/dev.sh/Containerfile/Dockerfile.dev/compose), yet the lifespan executes raw `UPDATE sessions …` / `UPDATE providers …` on boot. On a brand-new checkout (`make dev`) or a fresh production volume, those statements should raise `sqlite3.OperationalError: no such table: sessions`, failing app startup before the first request.

## Evidence
- `grep -rn "create_all\|alembic upgrade" backend/app Makefile dev.sh Containerfile backend/Dockerfile.dev .github` → no hits in any startup path.
- Lifespan writes: `backend/app/main.py:16-51` (raw `text("UPDATE …")`), invoked at `:66-67` before `yield`.
- Setup docs never mention migrations: `docs/docs/getting-started.md` (whole file), `README.md:38-47`; only `CLAUDE.md:222` mentions the alembic command exists.
- `.env.example:22-24` claims "The database file is created automatically on first run" — the *file* is, the tables are not.
- **Empirical confirmation** (executed during this review once the tooling outage lifted):
  ```
  $ DATABASE_URL="sqlite+aiosqlite:////tmp/eval_studio_fresh_test.db" uv run uvicorn app.main:app --port 8765
  …
  sqlite3.OperationalError: no such table: sessions
  sqlalchemy.exc.OperationalError: (sqlite3.OperationalError) no such table: sessions
  ERROR:    Application startup failed. Exiting.
  ```

## Impact
First-run experience is a crash for every new contributor and every fresh production volume. The CI container-smoke job would also hit this — but note it currently cannot even reach this point because the frontend build stage fails first (INFRA-008).

## Confidence note
Originally filed at `medium` from static analysis; upgraded to `high` after direct reproduction (above) on 2026-06-11.

## Root cause
Schema creation was left as an implicit manual step while startup logic (ARCH-008's migrations) silently began assuming the schema exists.

## Proposed fix (specification)
This is the symptom record; the canonical fix (run `alembic upgrade head` automatically at startup/entrypoint) is specified in INFRA-002. ARCH-008 removes the boot-time UPDATEs themselves.

## Alternatives considered
N/A — see INFRA-002.

## Verification
`rm -f backend/eval_studio.db*` (dev copy) → `make dev` → backend either crashes with "no such table" (bug confirmed) or serves `/api/v1/health` (bug refuted; downgrade to DOC-002 only).

## Relationship notes
- `superseded_by: INFRA-002` / `child_of: INFRA-002` — fully resolved by automatic migrations at startup; closes with it.
- `related: ARCH-008` — removing the lifespan UPDATEs eliminates this particular crash trigger but not the underlying "no schema on first run" gap (first query would still 500), which is why INFRA-002 is the canonical fix.
