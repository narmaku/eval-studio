---
id: SIMP-006
title: Prune dependencies: asyncssh (stub-only), mkdocs-material misplaced in backend deps, single-use form stack
category: simplification
severity: low
effort: S
confidence: high
breaking: false
status: open
depends_on: []
blocks: []
supersedes: []
superseded_by: []
conflicts_with: []
related: [SIMP-001, CONS-008, INFRA-004]
child_of: null
affected_paths:
  - backend/pyproject.toml
  - frontend/package.json
  - Makefile
---

## Problem
Three dependency findings: (1) `asyncssh` is a runtime dependency whose only import is the BYOE stub's availability check; (2) `mkdocs-material` lives in the **backend's** dev dependencies although it builds the top-level docs site — coupling docs tooling to the app venv and making `make docs-serve` work only by accident of directory layout (see INFRA-004); (3) `react-hook-form`/`@hookform/resolvers`/`zod` serve one component (CONS-008).

## Evidence
- `backend/pyproject.toml:16` (`asyncssh>=2.17,<3.0`); sole import `backend/app/environments/byoe.py:4` ("imported to verify dependency is available").
- `backend/pyproject.toml:29` (`mkdocs-material>=9.0` under `[project.optional-dependencies].dev`); used by `Makefile:62-66` (`cd docs && uv run mkdocs serve` — running the *backend's* venv from the docs directory).
- FE trio: `frontend/package.json:21,36,46`; single importer `components/datasets/DatasetUploadDialog.tsx:2-4`.

## Impact
Slower installs and bigger images for unused capability; the docs toolchain has no honest home; misleading signal about what the app actually does (SSH).

## Proposed fix (specification)
1. Remove `asyncssh` together with SIMP-001 (which deletes its importer). If SIMP-001 stalls, still remove it and drop the import line — the stub doesn't use it.
2. Give docs tooling a home: add `docs/pyproject.toml` with `mkdocs-material` (plus `mkdocs` pin) and remove it from backend dev deps; `make docs-serve` keeps working via `cd docs && uv run mkdocs serve` against the docs project (this also fixes INFRA-004 if confirmed). Alternative: a `dependency-group` at backend with an explicit comment — inferior, keeps the coupling.
3. FE form trio: per CONS-008's chosen direction.
4. Update `uv.lock`/`package-lock.json` accordingly.

## Alternatives considered
Keep asyncssh "for when environments land" — rejected: re-adding a dependency is one line on the day it's needed.

## Verification
`uv sync && uv run pytest` green without asyncssh; `make docs-serve` serves; `npm run build` green per CONS-008.

## Relationship notes
- `related: SIMP-001` — deletes asyncssh's importer; do step 1 with it.
- `related: CONS-008` — owns the FE form decision; this issue just executes the removal.
- `related: INFRA-004` — step 2 is the structural fix for the docs-serve target.
