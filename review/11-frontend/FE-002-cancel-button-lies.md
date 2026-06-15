---
id: FE-002
title: The Cancel button only forgets the evaluation client-side while it keeps running and spending tokens
category: frontend
severity: medium
effort: S
confidence: high
breaking: false
status: open
depends_on: [API-004]
blocks: []
supersedes: []
superseded_by: []
conflicts_with: []
related: []
child_of: null
affected_paths:
  - frontend/src/pages/QAEvaluation.tsx
  - frontend/src/pages/RAGEvaluation.tsx
  - frontend/src/pages/ArenaComparison.tsx
---

## Problem
The "Cancel" button during a run clears local state, disconnects the WS, and toasts "Evaluation cancelled" — but the server-side run continues to completion, consuming LLM tokens and writing results. There is no cancel API (see API-004). The user is told something happened that didn't.

## Evidence
- `frontend/src/pages/QAEvaluation.tsx:210-221`: `setCurrentEvaluation(null); clearRunningEvaluation(); clearLogs(); setPhase('configure'); toast('Evaluation cancelled');` — no API call.
- No cancel method exists: `grep -n "cancel" frontend/src/services/api.ts backend/app/api/v1/evaluations.py` → nothing.
- Same pattern on the RAG and Arena pages (their running-phase Cancel handlers mirror QA's).

## Impact
Real money/time spent after the user believes they stopped it; the evaluation later flips to "completed" in the dashboard, contradicting the toast; on arena runs (items × contestants) the waste is multiplied.

## Root cause
UI built assuming cancellation would exist (the phantom `cancelled` status, API-004); shipped with the local-only stub.

## Proposed fix (specification)
Tracks API-004's decision:
- If API-004 option A (real cancel endpoint): button calls `api.cancelEvaluation(id)`, keeps the WS open until the `cancelled` status event arrives, then resets phase. Toast only on server confirmation.
- If API-004 option B (no cancellation): relabel to "Stop watching" / "Back to setup", toast "Evaluation continues in background — see Results when finished", and surface the run in the dashboard as still running (it already does).

## Alternatives considered
Covered by the two tracks; keeping the current lying label is the only rejected option.

## Verification
Option A: cancel mid-run → backend status `cancelled`, no further Result rows, UI shows cancelled state. Option B: button copy changed in all three pages; eval continues and completes; notification appears on completion (existing `handleComplete` path).

## Relationship notes
- `depends_on: API-004` — the server-side decision determines which UI this becomes; implementing FE-002 first would have to guess.
