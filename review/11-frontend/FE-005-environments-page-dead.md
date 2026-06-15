---
id: FE-005
title: Environments page, types, and six API client methods target endpoints that always return 501
category: frontend
severity: low
effort: XS
confidence: high
breaking: false
status: open
depends_on: []
blocks: []
supersedes: []
superseded_by: [SIMP-001]
conflicts_with: []
related: []
child_of: SIMP-001
affected_paths:
  - frontend/src/pages/Environments.tsx
  - frontend/src/types/environment.ts
  - frontend/src/services/api.ts
  - frontend/src/App.tsx
---

## Problem
The FE ships a routed, nav-linked Environments page plus `types/environment.ts` and six `api.ts` methods, all of which can only ever produce 501 errors because every backend environments endpoint raises `NotImplementedException`.

## Evidence
- FE surface: `frontend/src/App.tsx:18,138-145` (route), `services/api.ts:178-188` (six methods), `pages/Environments.tsx`, `types/environment.ts`.
- Backend all-501: `backend/app/api/v1/environments.py:9-42`.

## Impact
A top-level nav destination that errors on use; dead types/client code maintained alongside live ones.

## Root cause
FE scaffolded in lockstep with the backend stub (SIMP-001's root cause).

## Proposed fix (specification)
Symptom record — SIMP-001 step 4 deletes all of it. No standalone action recommended (hiding the nav entry alone would leave the dead code).

## Alternatives considered
N/A.

## Verification
Covered by SIMP-001 (`tsc --noEmit`, no route, no nav entry).

## Relationship notes
- `superseded_by: SIMP-001` / `child_of: SIMP-001` — the FE slice of that deletion; closes with it.
