---
id: DOC-002
title: Setup docs omit the database migration step and use a wrong clone URL
category: docs
severity: medium
effort: XS
confidence: high
breaking: false
status: open
depends_on: [INFRA-002]
blocks: []
supersedes: []
superseded_by: []
conflicts_with: []
related: [DOC-001, SEC-005]
child_of: null
affected_paths:
  - docs/docs/getting-started.md
  - README.md
  - CONTRIBUTING.md
  - .env.example
---

## Problem
The quick starts (README, getting-started) walk a new user into the fresh-database failure (INFRA-002/BUG-006) by never mentioning `alembic upgrade head`; `.env.example` explicitly (and wrongly) reassures that the database "is created automatically on first run". The getting-started clone URL points at a nonexistent org (`github.com/eval-studio/eval-studio`) while in-code references use `narmaku/eval-studio`.

## Evidence
- No migration step: `docs/docs/getting-started.md:19-49`, `README.md:38-47`; `grep -rn "alembic" README.md CONTRIBUTING.md docs/docs/` → nothing.
- False reassurance: `.env.example:22-24`.
- URL mismatch: `docs/docs/getting-started.md:21,44` (`github.com/eval-studio/eval-studio`) vs `frontend/src/types/session.ts:17` (`github.com/narmaku/eval-studio/issues/106`); `docs/docs/adapters.md:16` also uses the eval-studio org URL for CONTRIBUTING.

## Impact
First-contact failure (until INFRA-002 lands) with no documented remedy; copy-pasted clone commands fail.

## Root cause
Docs written from the aspirational repo location; migration step lived only in maintainers' shell history.

## Proposed fix (specification)
After INFRA-002 (auto-migration) lands:
1. getting-started/README: state that schema migrations run automatically on startup; add the manual command in a "Troubleshooting / custom DATABASE_URL" note.
2. Fix all clone/CONTRIBUTING URLs to the real repo (`narmaku/eval-studio`, or whatever the canonical home is — confirm with the owner; do not leave two variants).
3. `.env.example:22-24`: reword to "schema is created/migrated automatically at startup".
4. While in getting-started: add the trust-model/bind note from SEC-004/SEC-005 (single sentence + link).

## Alternatives considered
Documenting the manual alembic step instead of fixing startup — rejected: INFRA-002 is strictly better; docs describe the end state.

## Verification
Fresh-clone walkthrough following only the docs succeeds on a clean machine (the INFRA-002 verification, executed via the documented commands).

## Relationship notes
- `depends_on: INFRA-002` — the text must describe post-fix behavior; writing it first would document the workaround.
- `related: DOC-001` (CLAUDE.md DB section), `SEC-005` (posture note).
