---
id: BUG-004
title: Harness registry computes the repo root one level short, so config/harnesses.yaml is never auto-discovered
category: bugs
severity: medium
effort: XS
confidence: high
breaking: false
status: done
depends_on: []
blocks: []
supersedes: []
superseded_by: []
conflicts_with: []
related: [DUP-002, ARCH-005]
child_of: DUP-002
affected_paths:
  - backend/app/harnesses/registry.py
---

## Problem
`harnesses/registry.py:_resolve_config_path` uses three `.parent` hops from a file at depth `backend/app/harnesses/`, landing on `backend/` instead of the repo root. Auto-discovery therefore looks for `backend/config/harnesses.yaml`; the documented location (`config/harnesses.yaml`, per `config/harnesses.yaml.example:3` "Copy this file to harnesses.yaml") is never found. The cwd fallback doesn't rescue it because both dev launchers run uvicorn from `backend/`.

## Evidence
- `backend/app/harnesses/registry.py:102`: `repo_root = Path(__file__).resolve().parent.parent.parent` → `…/backend`.
- Correct siblings use four hops from files at the same depth: `core/providers.py:131`, `core/tool_servers.py:127`, `adapters/registry.py:162` (`parent.parent.parent.parent`).
- cwd is `backend/` in both launchers: `Makefile:20` (`cd backend && … uvicorn`), `dev.sh:33-34`.

## Impact
Users who follow the example file's instructions get an empty harness list (UI shows no harnesses; subprocess-harness chats are impossible to configure via file). Only the env var `HARNESS_CONFIG_PATH` or API-created entries (which then persist to `backend/config/harnesses.yaml`, a path nothing documents) work.

## Root cause
`_resolve_config_path` copy-pasted from a registry whose file sits one directory shallower-adjusted, with the hop count edited wrong (DUP-002).

## Proposed fix (specification)
Point fix: change `:102` to `Path(__file__).resolve().parents[3]` (and prefer `parents[N]` over `.parent` chains in all four copies for readability). Structural fix: DUP-002/ARCH-005's shared resolver supersedes the point fix.

## Alternatives considered
Document `backend/config/` as the harness config home — rejected: inconsistent with the other three registries and the `.example` file.

## Verification
Place a minimal `config/harnesses.yaml` at repo root, start backend from `backend/`, `GET /api/v1/harnesses` returns the entry (fails today). Add this as a unit test using the resolver with monkeypatched paths.

## Relationship notes
- `child_of: DUP-002` — this is the live divergence that motivates the consolidation; remains open as a point fix candidate if DUP-002/ARCH-005 are scheduled later (Quick Win).
