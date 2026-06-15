---
id: SEC-004
title: Server-side requests to arbitrary user-supplied URLs are a design feature with no stated trust model
category: security
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
related: [SEC-005, SEC-003, BUG-005]
child_of: null
affected_paths:
  - backend/app/api/v1/providers.py
  - backend/app/agent_backends/custom_httpx_agent.py
  - backend/app/rag_backends/http_adapter.py
  - docs/docs/api-reference.md
---

## Problem
Four code paths make server-side HTTP requests to URLs taken directly from API input: provider `test_connection`, provider models listing, the custom-provider adapter, and the HTTP RAG adapter. From the backend host, these can reach anything the server can (cloud metadata endpoints, internal services). For a local single-user tool this is the product working as intended; for any shared deployment it is a textbook SSRF primitive. The repository nowhere states which deployment is supported, and it ships production compose/nginx assets implying shared deployment is expected.

## Evidence
- `backend/app/api/v1/providers.py:174-182` (`client.post(payload.endpoint_url, …)` — unauthenticated SSRF probe if auth is off), `:281-286` (`GET {api_base}/v1/models`).
- `backend/app/agent_backends/custom_httpx_agent.py:115-117` (POST to configured `endpoint_url` per message).
- `backend/app/rag_backends/http_adapter.py:52-54` (POST per dataset item).
- Shared-deployment artifacts exist: `docker-compose.prod.yml`, `nginx.conf`, `Containerfile` (OpenShift-compatible non-root user, `Containerfile:42-44`).

## Impact
Combined with SEC-005's default-open auth, any network peer can use the backend as a request proxy into its network (e.g. `POST /api/v1/providers/test` with `endpoint_url=http://169.254.169.254/…`). Response bodies are partially reflected (models list, connection messages).

## Root cause
"Register any model endpoint" is a core feature; the boundary where that stops being safe was never written down.

## Proposed fix (specification)
This issue's deliverable is a **decision + document + minimal guardrail**, not URL allowlisting machinery:
1. Write the trust model into `docs/docs/getting-started.md` + README ("eval-studio is a single-trust-domain tool: everyone who can reach the API/UI is fully trusted; it must not be exposed beyond that domain"), cross-referencing SEC-005's auth posture.
2. Guardrail proportional to the model: when `auth_disabled=True`, bind recommendation is localhost — see SEC-005 step 2 (compose/dev binding). No URL filtering while within the trust model.
3. Mark the four call sites with a one-line comment referencing the trust model so future hardening has a map.
4. Explicitly reject (in ROADMAP) building SSRF allowlists/egress proxies now — premature for the product stage; revisit if multi-tenant deployment ever becomes a goal.

## Alternatives considered
IP/range denylist (block link-local/RFC1918) — rejected for now: breaks the primary use case (local Ollama at `http://localhost:11434`, lab endpoints on private ranges).

## Verification
Docs contain the trust-model section; `grep -rn "trust model" backend/app` shows the four markers; SEC-005's binding change verified there.

## Relationship notes
- `related: SEC-005` — the auth/bind posture is the actual control for this risk; these two issues should land together as the "security posture" PR.
- `related: SEC-003, BUG-005` — concrete fixes that remain worthwhile inside the trust model.
