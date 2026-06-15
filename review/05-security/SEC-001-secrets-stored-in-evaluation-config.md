---
id: SEC-001
title: Auth headers and API keys travel inside evaluation.config and leak via API responses and artifacts
category: security
severity: high
effort: M
confidence: high
breaking: true
status: open
depends_on: []
blocks: []
supersedes: []
superseded_by: []
conflicts_with: []
related: [BUG-010, SEC-005]
child_of: null
affected_paths:
  - backend/app/services/rag_evaluation_service.py
  - backend/app/rag_backends/factory.py
  - backend/app/schemas/evaluation.py
  - backend/app/services/artifact_generation.py
  - frontend/src/components/evaluation/RAGEndpointConfig.tsx
---

## Problem
RAG evaluations carry live credentials in `config`: `rag_endpoint.auth_header` (a literal header dict, e.g. `{"Authorization": "Bearer …"}`) and `generator_api_key`/`connection_string` for the pgvector backend. That config is persisted verbatim in the `evaluations.config` JSON column, returned by every `GET /evaluations*` response (`EvaluationResponse.config`), and frozen into the downloadable `config.json` artifact. The provider subsystem deliberately avoids exactly this (`api_key_env` indirection, "Never exposes actual API key values") — the RAG path bypasses that design.

## Evidence
- Secret-bearing keys accepted from config: `backend/app/services/rag_evaluation_service.py:39-56` (`auth_header`, `generator_api_key`, `connection_string` passthrough), `rag_backends/factory.py:24-43`.
- Stored and returned: `models/evaluation.py:20` (JSON column), `schemas/evaluation.py:45` (`config` in every response, no redaction).
- Written to downloadable artifact: `services/artifact_generation.py:195-217` (`"config": evaluation.config or {}`).
- Design intent elsewhere: `schemas/provider.py:147` ("Never exposes actual API key values"), `api_key_env` mechanism `core/providers.py:32-37`.

## Impact
Any UI user (or anyone on the network given SEC-005's default-open posture) can read RAG endpoint bearer tokens and DB connection strings from list endpoints; tokens get baked into artifacts that users will download and share precisely because they look like harmless config snapshots.

## Root cause
RAG endpoint config was modeled as a free-form dict and reused the request payload as the persistence format.

## Proposed fix (specification)
1. Move secrets to env-indirection like providers: replace `auth_header` with `auth_header_name: str` + `auth_token_env: str` (and `generator_api_key` → `generator_api_key_env`); resolve at run time in `_build_rag_adapter_config`. Breaking change to the RAG config shape; update `RAGEndpointConfig.tsx` fields accordingly.
2. For `connection_string` (legitimately needed, contains password): store it but **redact on egress** — add a redaction pass before any config leaves the system:
   `def redacted_config(config: dict) -> dict` masking values of keys matching `(auth|token|key|secret|password|connection_string)` (case-insensitive), applied in `EvaluationResponse` serialization (validator on `config`) and in `_generate_config_json`.
3. Sweep existing rows: one-shot Alembic data migration nulling matching keys inside `evaluations.config` (best-effort JSON rewrite), since historical rows already contain tokens.

## Alternatives considered
Encrypt config at rest — wrong tool: the leak is egress, not storage; encryption adds key management without stopping the API/artifact exposure.

## Verification
- Integration: create RAG eval with `auth_token_env`; `GET /evaluations/{id}` and the generated `config.json` contain no token material; the adapter's outgoing request (respx) carries the resolved header.
- Grep-style test: response serializer masks a seeded `connection_string`.

## Relationship notes
- `related: BUG-010` — exception-borne variant of the same egress problem.
- `related: SEC-005` — the default-open posture multiplies this issue's blast radius; fixing either reduces total risk, both are needed.
