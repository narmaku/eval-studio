---
id: BUG-003
title: A malformed entry in providers/harnesses/tool_servers YAML crashes the whole registry load at import time
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
child_of: null
affected_paths:
  - backend/app/core/registry_base.py
  - backend/app/core/providers.py
  - backend/app/core/tool_servers.py
  - backend/app/harnesses/registry.py
---

## Problem
`load_from_yaml` guards only against non-dict entries; `_parse_item` in three of the four registries indexes required keys directly (`raw["id"]`, `raw["name"]`), so one entry missing `id` raises `KeyError` and aborts loading *all* entries. Because the registries load at module import (singleton blocks), a single bad line in `config/providers.yaml` prevents backend startup entirely. The evaluator registry shows the intended behavior (validate, warn, skip).

## Evidence
- Guard only for non-dict: `backend/app/core/registry_base.py:78-87` ("Malformed entries (non-dict or _parse_item returning None) are skipped" — KeyError is neither).
- Direct indexing: `core/providers.py:48-49`, `core/tool_servers.py:52-53` (and `t["name"]` at `:44`), `harnesses/registry.py:36-37`.
- Import-time load: `core/providers.py:145-148`, `core/tool_servers.py:139-141`, `harnesses/registry.py:114-116`.
- Correct pattern exists: `adapters/registry.py:47-53` (missing-field check with `logger.warning` + `return None`).
- Runtime reload has the same hole: `_check_reload` (`registry_base.py:90-103`) re-invokes `load_from_yaml`, so editing the YAML while running crashes the next API request instead of startup.

## Impact
Hand-editing a config file (an explicitly supported workflow — the `.example` files invite it) with one typo takes the whole backend down with a KeyError traceback rather than skipping the entry with a warning.

## Root cause
The skip-on-malformed contract was implemented only in the newest registry; the base class never enforced it.

## Proposed fix (specification)
1. Enforce in one place — wrap the parse call in `registry_base.load_from_yaml` (`:83`):
   ```python
   try:
       item = self._parse_item(raw)
   except (KeyError, TypeError, ValueError) as exc:
       logger.warning("registry.entry_invalid", entry=raw, error=str(exc), yaml_key=yaml_key)
       continue
   ```
2. Optionally align the three `_parse_item`s to the evaluator-style explicit required-field check for better messages (not required once step 1 exists).

## Alternatives considered
Fail-fast on bad config (crash deliberately) — rejected: contradicts the documented skip-with-warning contract and the evaluator registry's existing behavior; a config UI writes these files too.

## Verification
Extend `tests/unit/test_yaml_backed_registry.py`: YAML with one valid + one id-less entry → registry contains the valid one, log captured. Repeat via `_check_reload` (touch file).

## Relationship notes
- `related: DUP-002, ARCH-005` — same files under change; the base-class fix here is orthogonal and can land first as a quick win.
