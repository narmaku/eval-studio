---
id: DUP-002
title: Registry config-path resolution duplicated four times (one copy is wrong)
category: duplication
severity: medium
effort: S
confidence: high
breaking: false
status: open
depends_on: []
blocks: []
supersedes: []
superseded_by: []
conflicts_with: []
related: [ARCH-005, BUG-004]
child_of: null
affected_paths:
  - backend/app/core/providers.py
  - backend/app/core/tool_servers.py
  - backend/app/adapters/registry.py
  - backend/app/harnesses/registry.py
---

## Problem
Each of the four YAML registries carries its own `_resolve_config_path()` implementing the same three-step strategy (env override → repo-root `config/<file>` → cwd fallback). The four copies have already diverged: the harness copy computes the repo root with one fewer `.parent`, so it looks in `backend/config/` instead of `config/` (BUG-004).

## Evidence
- `backend/app/core/providers.py:117-142`, `core/tool_servers.py:121-136`, `adapters/registry.py:148-173` — all use `Path(__file__).resolve().parent.parent.parent.parent` (repo root, correct).
- `backend/app/harnesses/registry.py:96-111` — uses `parent.parent.parent` (= `backend/`, wrong) at `:102`.
- Each ends with an identical import-time singleton block (`providers.py:145-148`, `tool_servers.py:139-141`, `adapters/registry.py:176-179`, `harnesses/registry.py:114-116`).

## Impact
~80 duplicated lines; the divergence is a live bug; any change to discovery strategy (e.g. XDG config dir) needs four edits.

## Root cause
Each registry was cloned from the previous one; the harness clone dropped a `.parent` unnoticed.

## Proposed fix (specification)
Implemented by ARCH-005 steps 2–3: single `resolve_registry_config_path(explicit, filename)` in `core/registry_base.py`; four call sites; DELETE the four functions. If ARCH-005 is deferred, do the helper extraction alone (keeping `os.environ` reads as the `explicit` source) — same deletion, no Settings change.

## Alternatives considered
Point-fix only BUG-004 — rejected as the *whole* fix: leaves four copies; acceptable as an interim hotfix (see BUG-004).

## Verification
- `grep -rn "_resolve_config_path" backend/app` → only the shared helper.
- New unit test in `tests/unit/test_yaml_backed_registry.py`: helper returns env override verbatim; falls back to `<repo_root>/config/<name>`; harness registry finds a file placed at repo-root `config/harnesses.yaml` (fails today).

## Relationship notes
- `related: ARCH-005` — that issue's steps 2–3 are this consolidation plus Settings integration; close both together. Not marked superseded because this issue is independently implementable without the Settings change.
- `related: BUG-004` — the user-visible symptom of the divergence; fixed by either this consolidation or its own point-fix.
