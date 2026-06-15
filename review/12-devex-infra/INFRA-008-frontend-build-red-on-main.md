---
id: INFRA-008
title: Frontend production build is red on main — tsc reports 5 errors in test files, so the container image cannot build
category: devex-infra
severity: high
effort: S
confidence: high
breaking: false
status: open
depends_on: []
blocks: []
supersedes: []
superseded_by: []
conflicts_with: []
related: [INFRA-001, ARCH-004, TEST-003]
child_of: null
affected_paths:
  - frontend/src/stores/evaluationStore.test.ts
  - frontend/src/stores/providerStore.test.ts
  - frontend/src/stores/resultStore.test.ts
  - .github/workflows/ci.yml
---

## Problem
`npm run build` (`tsc -b && vite build`) fails on main with 5 type errors, all in store **test** files. Vitest passes (606/606) because it doesn't type-check, and CI has no tsc/build job — so the breakage is invisible until someone builds the production image: the `Containerfile`'s frontend stage runs `npm run build` and therefore cannot complete. Release builds (`release.yml`) and the CI container-smoke job are broken right now.

## Evidence
Executed during this review (verbatim, `00-meta/environment.md`):
```
src/stores/evaluationStore.test.ts(390,52): error TS2345 … missing the following properties from type 'Evaluation': average_score, pass_rate
src/stores/evaluationStore.test.ts(510,49): error TS2345 … missing … average_score, pass_rate
src/stores/providerStore.test.ts(31,3):    error TS2322: Type 'null' is not assignable to type 'string'.
src/stores/resultStore.test.ts(281,14):    error TS2532: Object is possibly 'undefined'.
src/stores/resultStore.test.ts(282,14):    error TS2532: Object is possibly 'undefined'.
```
- Build chain: `frontend/package.json:11` (`"build": "tsc -b && vite build"`); `Containerfile:11-12` (`COPY frontend/ .` then `RUN npm run build`).
- CI gap: `.github/workflows/ci.yml` frontend job runs only `npm ci` + `npm test -- --run` (`:68-84`) and lint; no `tsc`/`build` step outside the container-smoke docker build (`:86-93`), which therefore must currently fail.
- Root cause trail: the `Evaluation` type gained `average_score`/`pass_rate` (`frontend/src/types/evaluation.ts`, mirroring `schemas/evaluation.py:47-48` from the enriched-list feature) and test fixtures were not updated.

## Impact
The release pipeline and container smoke are broken on main; the only signal is a failed docker build. Test fixtures drifting from domain types is exactly the hand-mirroring failure mode ARCH-004 addresses, here biting *within* the frontend.

## Root cause
Type fields added to `Evaluation` without sweeping test fixtures; no fast CI step runs the type checker.

## Proposed fix (specification)
1. Fix the five errors: add `average_score: null, pass_rate: null` to the two evaluation fixtures (`evaluationStore.test.ts:390,510` objects); correct the provider fixture field typed `null` (`providerStore.test.ts:31` — likely `default_model: null` → `""`); guard or non-null-assert the two indexed accesses (`resultStore.test.ts:281-282`).
2. Add a CI step to the frontend job (cheap, catches this class permanently):
   ```yaml
   - name: Type-check frontend
     working-directory: frontend
     run: npx tsc -b --noEmit
   ```
   (or run full `npm run build`; tsc-only is faster and sufficient since container-smoke covers vite build).

## Alternatives considered
Exclude test files from `tsc -b` (separate tsconfig for build) — hides the drift instead of catching it; rejected.

## Verification
`npm run build` exits 0; `docker build -f Containerfile .` completes through the frontend stage; new CI step green and demonstrably fails if a fixture field is removed.

## Relationship notes
- `related: INFRA-001` — that issue makes the built UI *served*; this one makes it *buildable*. Both are required for a working production image; no ordering constraint between them.
- `related: ARCH-004` — same hand-mirrored-types disease; generated types would have flagged the fixture drift at authoring time.
- `related: TEST-003` — its smoke-depth item should assert the docker build itself stays green (already implicit in CI container-smoke once this is fixed).
