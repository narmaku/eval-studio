---
id: INFRA-003
title: make dev and dev.sh are divergent implementations of the same dev launcher
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
related: [ARCH-005, SEC-005, DOC-001]
child_of: null
affected_paths:
  - Makefile
  - dev.sh
---

## Problem
Two parallel dev launchers exist with meaningfully different behavior: `dev.sh` exports `.env` into the process environment (`set -a; source .env`) — which the registries' raw `os.environ` reads depend on — and skips `uv sync`/`npm install`; `make dev` installs dependencies but does not export `.env` (pydantic Settings still reads the file, but the registry path vars and `api_key_env` lookups silently don't work). Neither README nor CLAUDE.md mentions `dev.sh`; docs say `make dev`.

## Evidence
- `dev.sh:18-27` (env export, no installs) vs `Makefile:15-22` (installs, no export).
- Behavior split consequence: `core/providers.py:125` (`os.environ.get("PROVIDERS_CONFIG_PATH")`) and `ProviderProfile.api_key` (`core/providers.py:34-37`) see `.env` values only under `dev.sh`. A provider with `api_key_env: MY_KEY` set in `.env` works under `dev.sh` and silently has no key under `make dev`.
- Undocumented: `grep -rn "dev.sh" README.md CLAUDE.md docs/` → nothing.

## Impact
"Works on my machine" split along an invisible axis (which launcher you use); the API-key-env mechanism — the project's core secret-handling story — breaks under the documented launcher.

## Root cause
Convenience script added beside the Makefile target; no one reconciled them.

## Proposed fix (specification)
Keep one. Recommended: keep `dev.sh` as the implementation and make the Makefile target delegate:
1. Add `uv sync --quiet` / `npm install --silent` steps into `dev.sh` (cheap, idempotent) and keep its env-export + trap/cleanup (it's the more correct launcher).
2. `Makefile`: `dev: check-deps` runs `./dev.sh`.
3. Mention `dev.sh` in CONTRIBUTING for transparency.
(ARCH-005 reduces, but does not eliminate, the env-export dependency: `api_key_env` indirection legitimately needs exported env vars regardless.)

## Alternatives considered
Delete dev.sh and fix make dev (`set -a` inside the recipe) — equivalent outcome; recipe-embedded shell with traps is uglier than the script. Either is acceptable; pick one.

## Verification
`make dev` and `./dev.sh` behave identically: provider with `api_key_env` from `.env` resolves a key under both (add a startup debug log or check via `/api/v1/providers` `has_api_key: true`).

## Relationship notes
- `related: ARCH-005` — moves registry paths into Settings, shrinking the divergence to `api_key_env`; still worth unifying.
- `related: SEC-005` — host-binding default changes both launchers; combine edits.
- `related: DOC-001` — CLAUDE.md launcher documentation updates with this.
