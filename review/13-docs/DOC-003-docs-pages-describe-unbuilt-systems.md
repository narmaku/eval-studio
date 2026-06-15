---
id: DOC-003
title: docs/ pages assert capabilities that don't exist (environment providers, API-key-required-everywhere)
category: docs
severity: medium
effort: XS
confidence: high
breaking: false
status: done (superseded by SIMP-001)
depends_on: []
blocks: []
supersedes: []
superseded_by: [SIMP-001]
conflicts_with: []
related: [SEC-005, SIMP-004, DOC-001]
child_of: null
affected_paths:
  - docs/docs/environments.md
  - docs/docs/adapters.md
  - docs/docs/api-reference.md
---

## Problem
Three published docs pages state falsehoods as present-tense fact: environments.md claims "Supported providers include Docker Compose …, BYOE …, and TMT" (none are implemented; the API is all-501); adapters.md hedges with "coming soon" but still implies a working dual-adapter architecture; api-reference.md claims "All endpoints except /api/v1/health require a valid API key" (auth is off by default and WS never checks).

## Evidence
- `docs/docs/environments.md:8-11` ("Supported providers include…") vs `backend/app/api/v1/environments.py:9-42` (all 501) and `backend/app/environments/byoe.py` (stub).
- `docs/docs/api-reference.md:15-17` vs `core/config.py:27` (`auth_disabled=True` default) and SEC-002 (WS unauthenticated).
- `docs/docs/adapters.md:1-17` — describes the adapter/provider pattern as the working extension mechanism; the evaluator side is unwired (BUG-018).

## Impact
Docs are the project's claims to the outside world; present-tense fiction erodes trust in the accurate pages too.

## Root cause
Pages written from the roadmap, not the code.

## Proposed fix (specification)
Largely absorbed by other issues: SIMP-001 step 6 rewrites/deletes environments.md; SEC-005 step 4 fixes the api-reference auth section. Residual standalone work: adapters.md — either delete the page (if SIMP-002 wins) or rewrite around the genuinely pluggable parts (agent backends, RAG backends, harnesses) with one honest paragraph each.

## Alternatives considered
Banner-disclaimer at the top of each page — rejected: fixing three short pages costs less than maintaining disclaimers.

## Verification
`make docs-build` green; a read-through finds no present-tense claim contradicted by `grep` (the DOC-001 checklist script can cover docs/ paths too).

## Relationship notes
- `superseded_by: SIMP-001` — its docs step covers the biggest page; if SIMP-001 is rejected, this issue reopens in full as the honest-rewrite fallback.
- `related: SEC-005` (api-reference auth text), `SIMP-004` (ci-cd-integration.md rewrite handled there), `DOC-001` (same verification tooling).
