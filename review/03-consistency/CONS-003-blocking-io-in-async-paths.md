---
id: CONS-003
title: Synchronous file I/O runs on the event loop in async request paths
category: consistency
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
related: [ARCH-005]
child_of: null
affected_paths:
  - backend/app/core/registry_base.py
  - backend/app/api/v1/evaluators.py
  - backend/app/api/v1/artifacts.py
---

## Problem
Several async endpoints perform blocking file I/O directly on the event loop: every registry read triggers an mtime `stat` (and possibly a full YAML parse) via `_check_reload()`, registry writes dump YAML synchronously, evaluator config files are read/written with `Path.read_text`/`write_bytes`, and artifact previews read up to 1 MB synchronously.

## Evidence
- `backend/app/core/registry_base.py:63-103` (`load_from_yaml`/`_check_reload`: `open`, `yaml.safe_load`, `os.path.getmtime`) and `:171-183` (`_persist_yaml`: sync write) — called from async routes via e.g. `api/v1/providers.py:188`.
- `backend/app/api/v1/evaluators.py:148-152` (`file.read()` is async, but `target_path.write_bytes` is sync), `:190` (`read_text`), `:167-171` (directory iteration + stat).
- `backend/app/api/v1/artifacts.py:127` (`read_text` up to `PREVIEW_MAX_SIZE` = 1 MB, `:20`).

## Impact
At this product's scale (small YAML files, 1 MB cap) stalls are single-digit milliseconds — but during a stall *all* concurrent work freezes, including WS streaming of running evaluations. The codebase otherwise enforces "all I/O is async" (CLAUDE.md coding conventions), so this is an internal consistency break more than a performance emergency.

## Root cause
Registries and file endpoints were written sync-first because they predate heavy WS streaming.

## Proposed fix (specification)
1. Wrap the hot writes/reads in `asyncio.to_thread`: `_persist_yaml` (make `add_item/update_item/delete_item` async or wrap at router call sites via the DUP-009 `registry_write` helper — preferred, no ABC signature churn), `write_bytes`/`read_text` in `evaluators.py`, `read_text` in `artifacts.py`.
2. Leave `_check_reload`'s `getmtime` as-is (a single stat; wrapping every read is not worth it) — note this decision in code once, not per call.

## Alternatives considered
aiofiles dependency — rejected: `asyncio.to_thread` covers these few sites without a new dep.

## Verification
`uv run pytest` green; sanity: artifact preview of a 1 MB file while a WS client receives progress events shows no gap (manual).

## Relationship notes
- `related: ARCH-005` — registry internals are being touched there; coordinate to avoid conflicting edits to `registry_base.py`.
