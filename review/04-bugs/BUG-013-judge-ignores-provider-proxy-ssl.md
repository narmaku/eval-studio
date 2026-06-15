---
id: BUG-013
title: Judge LLM calls ignore the judge provider's proxy and SSL settings
category: bugs
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
related: [BUG-011, DUP-006]
child_of: null
affected_paths:
  - backend/app/adapters/litellm_judge.py
  - backend/app/adapters/factory.py
  - backend/app/services/evaluation_service.py
  - backend/app/services/arena_evaluation_service.py
  - backend/app/services/rag_evaluation_service.py
  - backend/app/api/v1/sessions.py
---

## Problem
`LiteLLMJudgeAdapter` is constructed with only `model/api_key/api_base` — the judge provider's `proxy`, `ssl_cert_path`, and `ssl_client_key` are resolved (they're on the `ResolvedModel`) but never passed in, and none of its three `acompletion` calls is wrapped in `proxy_env`. The model-under-test path honors these settings (`call_model`); the judge path silently doesn't.

## Evidence
- Construction sites drop the fields: `services/evaluation_service.py:151-157`, `arena_evaluation_service.py:128-134`, `rag_evaluation_service.py:167-173`, `api/v1/sessions.py:204-208` — all pass only model/key/base, though `judge_resolved.proxy/ssl_cert_path/ssl_client_key` exist (`provider_utils.py:123-137`).
- Adapter constructor accepts no proxy/ssl: `adapters/litellm_judge.py:143-155`; calls at `:186, :285, :360` without `proxy_env` (contrast `call_model`, `provider_utils.py:321-322`, and the agent adapter, `agent_backends/litellm_agent.py:79`).

## Impact
In any environment that needs a proxy or custom CA (the exact corporate scenario the provider fields exist for), the model-under-test call succeeds and the judge call fails with connection/TLS errors — every item scores as an error. Confusing because "the same provider works" elsewhere.

## Root cause
Adapter predates the proxy/SSL feature; only `call_model` was upgraded.

## Proposed fix (specification)
1. Extend `LiteLLMJudgeAdapter.__init__` with `proxy`, `ssl_cert_path`, `ssl_client_key` (mirroring `LiteLLMAgentAdapter`, `agent_backends/litellm_agent.py:22-36`).
2. Apply them around each judge call — preferably via BUG-011's per-client mechanism; interim: `with proxy_env(self.proxy, self.ssl_cert_path, self.ssl_client_key):` inside DUP-006's `_ask_judge` helper (one site).
3. Thread the three fields at the four construction sites from `judge_resolved`.

## Alternatives considered
Route judge calls through `call_model` — attractive unification, but judge calls need `response_format=json_object` and per-mode prompts; the adapter is the right seam.

## Verification
Unit (respx/litellm mock): judge provider with `proxy` set → assert outgoing call carries proxy routing (or `proxy_env` activated). Existing judge tests stay green.

## Relationship notes
- `related: BUG-011` — the *mechanism* for applying proxy/SSL should be the per-client one chosen there; this issue is about the judge path being wired at all.
- `related: DUP-006` — the single `_ask_judge` helper is where step 2 lands once.
