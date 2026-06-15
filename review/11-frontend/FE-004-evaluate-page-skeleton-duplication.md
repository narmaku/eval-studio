---
id: FE-004
title: The four evaluate pages re-implement the same configure/running/complete state machine
category: frontend
severity: low
effort: M
confidence: high
breaking: false
status: open
depends_on: []
blocks: []
supersedes: []
superseded_by: []
conflicts_with: []
related: [CONS-008, FE-002]
child_of: null
affected_paths:
  - frontend/src/pages/QAEvaluation.tsx
  - frontend/src/pages/RAGEvaluation.tsx
  - frontend/src/pages/ArenaComparison.tsx
  - frontend/src/pages/AgentEvaluation.tsx
---

## Problem
QA, RAG, and Arena pages (and partially Agent) each hand-roll the same machinery: `PagePhase` state, `getInitialPhase()` reading the same sessionStorage key, the auto-resume effect, `handleStart` building a `CreateEvaluationRequest` + `createAndRunEvaluation` + toasts, `handleComplete` with the same three-status notification block, the Cancel handler, and `handleNewEvaluation` reset. Only the config-panel composition and results table differ.

## Evidence
- `frontend/src/pages/QAEvaluation.tsx:20-50` (`PagePhase`, `getInitialPhase`, resume effect) — mirrored in `RAGEvaluation.tsx` and `ArenaComparison.tsx` (same `getInitialPhase` with mode literal swapped; 270/267-line files).
- `handleComplete`'s completed/failed/cancelled notification block: `QAEvaluation.tsx:106-146` duplicated per page.
- Cancel handler duplication: see FE-002 evidence.

## Impact
~400 duplicated lines; behavior fixes (FE-002's cancel relabel, notification changes) must be made three or four times and have already drifted in small ways (Agent page diverges most, 521 lines).

## Root cause
Pages copied from QAEvaluation as modes were added.

## Proposed fix (specification)
1. Extract `useEvaluationRun(mode: EvaluationMode)` hook owning: phase state + sessionStorage resume, `start(request)` (create/run/toast/notify), `handleComplete` (toasts + notifications + phase), `cancel()` (per FE-002's resolution), `reset()`.
2. Optionally an `<EvaluationRunShell phase={…} configure={…} results={…} />` layout component for the running/complete chrome (progress + cancel + new-evaluation button).
3. Each page reduces to its config panels + results table + hook wiring (target: QA/RAG/Arena ≤120 lines each). Agent page adopts only the pieces that fit its session model — don't force it.
4. Net deletion ≈ 350 lines.

## Alternatives considered
One mega-page with mode switch — rejected: the per-mode config forms are genuinely different; route-level separation is right, only the lifecycle is shared.

## Verification
Existing page tests (`QAEvaluation`-area tests, `ArenaComparison.test.tsx`, `AgentEvaluation.test.tsx`) pass against the hook; one new hook test covers resume-from-sessionStorage and complete-notification behavior once instead of four times.

## Relationship notes
- `related: FE-002` — implement the cancel resolution inside the hook so it lands once.
- `related: CONS-008` — both reduce FE pattern divergence; independent.
