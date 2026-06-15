---
id: BUG-005
title: Custom-provider request templates substitute {{message}} by raw string replace, breaking/injecting JSON
category: bugs
severity: high
effort: XS
confidence: high
breaking: false
status: done
depends_on: []
blocks: []
supersedes: []
superseded_by: []
conflicts_with: []
related: [SEC-004, BUG-017]
child_of: null
affected_paths:
  - backend/app/agent_backends/custom_httpx_agent.py
  - backend/app/api/v1/providers.py
---

## Problem
The custom HTTP provider builds its request body by textually replacing `{{message}}` inside a JSON template and then `json.loads`-ing the result. Any user message containing a double quote, backslash, or newline produces invalid JSON (request fails with `json.JSONDecodeError`), and a crafted message can inject arbitrary JSON structure into the request (e.g. extra fields), since no escaping is applied. The provider test endpoint repeats the same substitution.

## Evidence
- `backend/app/agent_backends/custom_httpx_agent.py:84-85`:
  ```python
  rendered = self.request_body_template.replace("{{message}}", last_user_msg)
  return json.loads(rendered)
  ```
- Same pattern in `backend/app/api/v1/providers.py:166-171` (test_connection, with constant "test" so only latently wrong there).
- Reachable from QA evals too: `call_model` routes custom providers through this adapter (`services/provider_utils.py:291-307`), where `question` is arbitrary dataset content — datasets with quotes/newlines (extremely common) break every item.

## Impact
Custom providers fail on realistic inputs (any question containing `"` or a newline); dataset-controlled JSON injection into request bodies sent to the configured endpoint. Functional severity high; security impact bounded by SEC-004's trust model (the endpoint is user-configured).

## Root cause
Template substitution implemented as string replace instead of JSON-aware substitution.

## Proposed fix (specification)
1. Replace string substitution with JSON-escaped substitution in `_build_request_body`:
   ```python
   escaped = json.dumps(last_user_msg)[1:-1]   # escape, strip surrounding quotes
   rendered = self.request_body_template.replace("{{message}}", escaped)
   ```
   This keeps the documented template contract (`{{message}}` sits inside a JSON string literal) while making any message safe.
2. Wrap the final `json.loads(rendered)` in a try/except raising `ValueError(f"request_body_template does not produce valid JSON: …")` so template bugs surface as clean errors (pairs with BUG-017's error-handling fix in the same adapter).
3. Apply the same escaping in `providers.py:167`.
4. Document in the `request_body_template` field description (`schemas/provider.py:92-98`) that the placeholder must appear inside a JSON string.

## Alternatives considered
Structured templates (parse template JSON, walk and substitute placeholders in string values) — more robust (placeholder could be outside a string), but heavier; the escape approach covers the documented usage exactly.

## Verification
Unit tests in `tests/unit/test_custom_httpx_adapter.py`: message with `"` / newline / backslash round-trips into the request body intact (assert via respx-captured request JSON); malicious `", "admin": true, "x": "` stays a literal string value.

## Relationship notes
- `related: SEC-004` — the injection half is a security concern subordinated to the declared trust model; the functional half stands alone.
- `related: BUG-017` — same adapter, complementary error-handling fix; land together.
