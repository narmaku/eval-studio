---
id: ARCH-005
title: Two configuration mechanisms: pydantic Settings vs direct os.environ reads in registries
category: architecture
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
related: [CONS-001, DUP-002, ARCH-002]
child_of: null
affected_paths:
  - backend/app/core/config.py
  - backend/app/core/providers.py
  - backend/app/core/tool_servers.py
  - backend/app/adapters/registry.py
  - backend/app/harnesses/registry.py
---

## Problem
App configuration is split between the `Settings` class (env + `.env`, typed, documented) and raw `os.environ.get()` calls inside the four YAML registries for `PROVIDERS_CONFIG_PATH`, `TOOL_SERVERS_CONFIG_PATH`, `EVALUATORS_CONFIG_PATH`, `HARNESS_CONFIG_PATH`. The registry variables therefore don't load from `.env` via pydantic, don't appear in one inspectable settings object, and each registry re-implements its own path-resolution function (one of them incorrectly — BUG-004).

## Evidence
- `backend/app/core/config.py:8-60` — Settings has no `*_config_path` fields.
- Raw env reads: `backend/app/core/providers.py:125`, `core/tool_servers.py:123`, `adapters/registry.py:156`, `harnesses/registry.py:98`.
- `.env.example:67-82` documents these four variables as if they were ordinary settings.
- Note: because `Settings` loads `.env` only into the *process settings object* (pydantic does not export to `os.environ`), setting `PROVIDERS_CONFIG_PATH` in `.env` works under `dev.sh` (which `set -a`-exports the file, `dev.sh:19-23`) but NOT under `make dev` (no export, `Makefile:15-22`) — the same variable behaves differently depending on the launcher.

## Impact
Config behavior depends on which dev launcher you use; four copies of path resolution drift (BUG-004 is one of them); there is no single place to see effective configuration.

## Root cause
Registries were written as self-contained modules with import-time singletons; pulling settings in at import time was avoided ad hoc rather than designed.

## Proposed fix (specification)
1. Add to `Settings` (`core/config.py`):
   ```python
   providers_config_path: str | None = None
   tool_servers_config_path: str | None = None
   evaluators_config_path: str | None = None
   harnesses_config_path: str | None = None
   ```
   (env names match the existing variables by pydantic convention; `HARNESS_CONFIG_PATH` → rename setting/env to `HARNESSES_CONFIG_PATH` with the old name kept only in `.env.example` history note — breaking-but-unreleased.)
2. Move the shared fallback logic into one function in `core/registry_base.py`:
   `def resolve_registry_config_path(explicit: str | None, filename: str) -> Path` implementing override → repo-root `config/<filename>` → cwd fallback (single, correct repo-root computation: `Path(__file__).resolve().parents[3]`, matching `core/config.py:5`).
3. Each registry module calls `resolve_registry_config_path(settings.providers_config_path, "providers.yaml")` etc.; DELETE the four `_resolve_config_path()` copies.
4. This also fixes BUG-004 (harness path) structurally; BUG-004 stays open only if a point-fix lands first.

## Alternatives considered
1. Keep raw env reads but centralize the helper — rejected: still two config systems, still invisible in Settings.
2. Lazy registries constructed at app startup with injected settings — better design, but bigger refactor for little additional payoff here; can ride ARCH-001/later work.

## Verification
- `uv run pytest tests/unit/test_yaml_backed_registry.py tests/unit/test_yaml_reload.py` green.
- Set `PROVIDERS_CONFIG_PATH=/tmp/p.yaml` in `.env` only (no shell export), start via `make dev`, confirm the registry uses it (it does not today).

## Relationship notes
- `related: DUP-002` — DUP-002 documents the 4× `_resolve_config_path` copies; step 2/3 here implements that consolidation. DUP-002 is kept as the symptom record and should be closed together with this issue (not marked superseded because a minimal DUP-002-only fix is possible without the Settings change).
- `related: BUG-004` — fixed structurally by step 2; see that issue for the standalone point-fix.
- `related: CONS-001` — `.env.example` cleanup must reflect the final variable names from step 1.
- `related: ARCH-002` — both reduce "two mechanisms for one concern"; independent.
