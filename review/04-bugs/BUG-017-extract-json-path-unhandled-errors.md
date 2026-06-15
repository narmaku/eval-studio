---
id: BUG-017
title: extract_json_path crashes with raw KeyError/IndexError/TypeError on unexpected response shapes
category: bugs
severity: low
effort: XS
confidence: high
breaking: false
status: done
depends_on: []
blocks: []
supersedes: []
superseded_by: []
conflicts_with: []
related: [BUG-005]
child_of: null
affected_paths:
  - backend/app/agent_backends/custom_httpx_agent.py
---

## Problem
`extract_json_path` walks the user-configured `response_json_path` with bare indexing — a response that doesn't match the configured path raises `KeyError`/`IndexError`/`TypeError` deep inside the chat stream or eval item, surfacing as the generic sanitized "internal error" with no hint that the JSON path is wrong. Numeric segments also only work on lists (`choices.0` works, but a dict with key `"0"` doesn't, and a non-numeric segment against a list raises `ValueError` from `int()`).

## Evidence
`backend/app/agent_backends/custom_httpx_agent.py:23-31`:
```python
for segment in path.split("."):
    current = current[int(segment)] if isinstance(current, list) else current[segment]
```
Callers: `:119-120` (chat/eval path), used per item via `call_model` (`provider_utils.py:291-307`).

## Impact
The most common custom-provider misconfiguration (wrong path) produces the least diagnosable failure mode; users can't distinguish "endpoint broken" from "path wrong".

## Root cause
Happy-path helper; error mapping never added.

## Proposed fix (specification)
Wrap the walk and raise a configured-input error:
```python
try:
    current = current[int(segment)] if isinstance(current, list) else current[segment]
except (KeyError, IndexError, TypeError, ValueError) as exc:
    raise ValueError(
        f"response_json_path '{path}' failed at segment '{segment}': {exc.__class__.__name__}"
    ) from exc
```
`ValueError` is preserved by `sanitize_error_for_client` (`core/exceptions.py:80-81`), so the message reaches the user as intended.

## Alternatives considered
Return None and treat as empty response — rejected: hides misconfiguration.

## Verification
`tests/unit/test_custom_httpx_adapter.py`: response `{"a": {}}` with path `a.b.c` → ValueError whose message names the path and segment; WS error envelope shows it (existing sanitize tests cover propagation).

## Relationship notes
- `related: BUG-005` — same adapter; land as one PR.
