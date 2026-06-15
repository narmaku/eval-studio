---
id: BUG-011
title: proxy_env mutates process-global state; concurrent evaluations with different proxies/certs race
category: bugs
severity: medium
effort: M
confidence: high
breaking: false
status: open
depends_on: []
blocks: []
supersedes: []
superseded_by: []
conflicts_with: []
related: [BUG-013, DUP-006]
child_of: null
affected_paths:
  - backend/app/services/provider_utils.py
  - backend/app/agent_backends/litellm_agent.py
---

## Problem
`proxy_env` configures per-provider proxy/SSL by mutating `os.environ` (`HTTP(S)_PROXY`, `SSL_CERT_FILE`, …) and the module-global `litellm.ssl_certificate` for the duration of a call. Evaluations run with `max_concurrency=10` and multiple evaluations/sessions run concurrently, so calls with different providers interleave: one task's restore step can strip another task's still-needed proxy, and mTLS certs can be applied to the wrong provider's request. The code itself admits the race ("Acceptable for MVP").

## Evidence
- `backend/app/services/provider_utils.py:217-270`, esp. the comment `:228-231` ("both env vars and litellm.ssl_certificate are process-global. For concurrent calls with different providers this could race.").
- Concurrent usage: `call_model` wraps every QA/arena model call (`provider_utils.py:321-322`) under `asyncio.Semaphore(10)` fan-out (`evaluation_service.py:248-258`); the agent adapter holds it across an entire **streaming** response (`agent_backends/litellm_agent.py:79-117`), maximizing the overlap window.

## Impact
With two providers where at least one sets proxy/SSL: nondeterministic connection failures, traffic egressing through the wrong (or no) proxy, mTLS handshake failures. Invisible at single-provider usage, which is why it survives.

## Root cause
LiteLLM's surface makes per-call proxy/cert awkward, so env mutation was the expedient path.

## Proposed fix (specification)
Prefer passing connection options per call instead of ambient state:
1. litellm accepts httpx-style client options per call: pass `client_session`/`ssl_verify`-equivalents — concretely, construct a per-provider `httpx.AsyncClient(proxy=…, verify=…, cert=…)` and pass it via `litellm.acompletion(..., client=...)` if the pinned litellm version supports it; otherwise use `litellm.Router` per provider with `client_args`. (Implementation must check the pinned `litellm>=1.40,<1.50` API; both mechanisms exist in that range — pick the one that passes the verification test below.)
2. Cache one client per provider id (dict in `provider_utils`), reuse across items.
3. Keep `proxy_env` only as a last-resort fallback wrapped in an `asyncio.Lock` (serializing only the calls that need ambient config), so misconfigured combinations degrade to slow-but-correct.
4. Delete the env mutation from the streaming agent path in favor of the same per-client mechanism.

## Alternatives considered
Global `asyncio.Lock` around every proxied call — trivially correct but serializes all LLM traffic for proxy users; acceptable interim hotfix (one-line risk reduction) but not the end state.

## Verification
Integration-style unit test with two fake providers (respx): provider A with proxy, provider B without, 20 interleaved `call_model` tasks → assert B's requests never carry proxy routing and A's always do. Today this test fails intermittently.

## Relationship notes
- `related: BUG-013` — the judge adapter currently has *no* proxy support; give it the same per-client mechanism rather than the buggy ambient one.
- `related: DUP-006` — the judge-call helper created there is where the judge side of this fix plugs in.
