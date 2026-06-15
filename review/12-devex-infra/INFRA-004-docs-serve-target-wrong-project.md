---
id: INFRA-004
title: make docs-serve runs uv from docs/, a directory with no Python project
category: devex-infra
severity: low
effort: XS
confidence: high
breaking: false
status: open
depends_on: []
blocks: []
supersedes: []
superseded_by: []
conflicts_with: []
related: [SIMP-006]
child_of: null
affected_paths:
  - Makefile
  - docs/
  - backend/pyproject.toml
---

## Problem
`make docs-serve`/`docs-build` execute `cd docs && uv run mkdocs serve|build`, but `docs/` contains only `mkdocs.yml` and markdown — no `pyproject.toml`. `uv run` outside a project either fails ("no project found") or silently resolves to some parent/ephemeral environment that does not include `mkdocs-material` (which is declared in the **backend's** dev extras). Either way, the documented docs workflow doesn't use the environment that declares its dependency.

## Evidence
- `Makefile:62-66` (`cd docs && uv run mkdocs serve`).
- `ls docs/` → `mkdocs.yml`, `docs/` (pages) only — no pyproject (file inventory).
- `mkdocs-material` lives in `backend/pyproject.toml:29` dev extras.

## Impact
Docs can't be built by following the Makefile. **Confirmed by execution** during this review:
```
$ make docs-build
cd docs && uv run mkdocs build
error: Failed to spawn: `mkdocs`
  Caused by: No such file or directory (os error 2)
make: *** [Makefile:66: docs-build] Error 2
```
(Confidence upgraded medium → high accordingly.)

## Root cause
Docs tooling parked in the backend's deps (SIMP-006 item 2) while the Make target assumed a docs-local project.

## Proposed fix (specification)
Implemented by SIMP-006 step 2 (give `docs/` its own minimal `pyproject.toml` with mkdocs-material). Alternative one-liner if SIMP-006 is deferred: change the targets to `cd backend && uv run mkdocs serve -f ../docs/mkdocs.yml`.

## Alternatives considered
`uvx mkdocs-material` style ephemeral run — pins nothing; rejected.

## Verification
Fresh clone: `make docs-serve` serves the site on mkdocs' default port; `make docs-build` emits `site/` (which `make clean` already expects, `Makefile:51`).

## Relationship notes
- `related: SIMP-006` — its step 2 is the structural fix; this issue tracks the broken target and the fallback one-liner.
