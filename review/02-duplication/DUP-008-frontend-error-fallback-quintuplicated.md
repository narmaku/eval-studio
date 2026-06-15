---
id: DUP-008
title: api.ts repeats the error-body fallback + throw block five times
category: duplication
severity: low
effort: XS
confidence: high
breaking: false
status: open
depends_on: []
blocks: []
supersedes: []
superseded_by: []
conflicts_with: []
related: [ARCH-004]
child_of: null
affected_paths:
  - frontend/src/services/api.ts
---

## Problem
The 10-line "parse ProblemDetail or synthesize one, then throw ApiClientError" block is duplicated in the generic `request()` helper and in four bespoke fetchers that bypass it (multipart upload ×2, text responses ×2).

## Evidence
`frontend/src/services/api.ts:65-74` (request), `:163-172` (analyzeDatasetFiles), `:284-293` (uploadEvaluatorConfigFile), `:303-311` (getEvaluatorConfigFile), `:352-361` (previewArtifact).

## Impact
Five copies of error semantics; the four bespoke fetchers exist only because `request()` hardcodes a JSON `Content-Type` header and `response.json()` body parsing.

## Root cause
`request()` wasn't parameterized for FormData/text, so callers forked it.

## Proposed fix (specification)
1. Generalize the helper:
   ```ts
   async function request<T>(path: string, options?: RequestInit & { parse?: 'json' | 'text' }): Promise<T>
   ```
   - Set `Content-Type: application/json` only when the body is a string (FormData callers pass the body through; the browser sets the boundary header).
   - After the shared error check, return `parse === 'text' ? response.text() : response.json()`.
2. Rewrite the four bespoke fetchers as one-liners over `request` (FormData body / `parse: 'text'`); DELETE their inline error blocks (≈40 lines).

## Alternatives considered
Adopt a fetch wrapper lib (ky/axios) — rejected: 40 lines of vanilla fetch don't justify a dependency.

## Verification
`npm test -- --run` green (stores mock `api`, so behavior-level tests are unaffected); manual: upload a dataset file and preview an artifact.

## Relationship notes
- `related: ARCH-004` — type generation changes the types `request<T>` is instantiated with, not this helper's shape; no ordering constraint.
