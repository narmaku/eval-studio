---
id: DUP-009
title: Providers/harnesses/tool-servers routers are three copies of one YAML-CRUD router shape
category: duplication
severity: low
effort: M
confidence: high
breaking: false
status: open
depends_on: []
blocks: []
supersedes: []
superseded_by: []
conflicts_with: []
related: [CONS-004, DUP-010]
child_of: null
affected_paths:
  - backend/app/api/v1/providers.py
  - backend/app/api/v1/harnesses.py
  - backend/app/api/v1/tool_servers.py
---

## Problem
Three routers implement the same five endpoints (list/get/post/put/delete) over a `YAMLBackedRegistry` with the same patterns: uuid4 id generation, `_to_response` mapper, `model_dump(exclude_unset=True)` update, RuntimeError→500 mapping, NotFound mapping. Harnesses and tool-servers additionally duplicate the allowlist-validation preamble.

## Evidence
- `backend/app/api/v1/providers.py:185-244`, `harnesses.py:53-133`, `tool_servers.py:53-134` — same endpoint sequence and bodies modulo names.
- Allowlist preamble: `harnesses.py:21-34` vs `tool_servers.py:20-33` (same structure, different settings key).
- RuntimeError→AppException(500) mapping ×6: `harnesses.py:92-95,113-116,126-129`; `tool_servers.py:89-92,115-118,127-130` (providers router omits it — a behavioral inconsistency: a failed YAML write there surfaces as an unhandled 500 without sanitization).

## Impact
~250 lines of parallel code; the providers router's missing RuntimeError handling shows the copies already diverge in error behavior.

## Root cause
Routers cloned as each registry was added.

## Proposed fix (specification)
This is a *deliberate* judgment call: a generic CRUD-router factory adds indirection for three resources. Recommended middle path:
1. Extract the genuinely shared, divergence-prone parts into `backend/app/api/v1/_registry_helpers.py`: `def registry_write(fn, *args)` (RuntimeError→AppException(500) with sanitize) and `def validate_allowlisted_command(command, allowed_env_value, context)` used by both harness and tool-server validation preambles.
2. Apply `registry_write` in all three routers (fixes the providers gap).
3. Do NOT genericize the endpoint bodies themselves — the response mappers and validation differ enough that a factory would obscure more than it saves.

## Alternatives considered
Full generic `build_registry_router(registry, schemas)` factory — rejected: saves ~150 lines but couples three resources' API evolution; revisit only if a fourth registry appears.

## Verification
`uv run pytest tests/integration/test_providers_api.py tests/integration/test_harnesses_api.py tests/integration/test_tool_servers_api.py` green; simulate a read-only `config/` dir and confirm provider create now returns a sanitized 500 instead of a raw traceback.

## Relationship notes
- `related: CONS-004` — these routers return bare lists while DB resources paginate; that shape decision is CONS-004's.
- `related: DUP-010` — provider response mapping is part of the shape consolidation there.
