---
id: PERF-002
title: Evaluation log buffer grows unbounded and re-allocates per WS message, re-rendering the log panel per line
category: performance
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
related: [FE-001]
child_of: null
affected_paths:
  - frontend/src/stores/evaluationStore.ts
  - frontend/src/components/evaluation/EvaluationLogPanel.tsx
---

## Problem
Every WS `log` message creates a brand-new `logs` array (`[...state.logs, data]`) with no cap. A large evaluation emits ≥4 log lines per item (processing/response/score + progress), so a 1,000-item run produces 4,000+ messages, each triggering an O(n) array copy and a re-render of the log panel — quadratic total work, growing memory, and a visibly janky log view late in big runs.

## Evidence
- `frontend/src/stores/evaluationStore.ts:186-189`:
  ```ts
  } else if (data.type === 'log') {
    set((state) => ({ logs: [...state.logs, data] }));
  ```
  No cap anywhere; `clearLogs` only on user action (`:244`).
- Per-item emission rate: `backend/app/services/evaluation_service.py:189-221` (3 broadcast_log per item + progress).
- Contrast: notifications cap at 50 (`notificationStore.ts:17,50`).

## Impact
Noticeable UI degradation on the exact runs where users watch logs most (big evals); unbounded memory for long arena runs (items × contestants).

## Root cause
Append-only store written for demo-sized runs.

## Proposed fix (specification)
1. Cap the buffer (ring): `const MAX_LOGS = 500;` → `logs: [...state.logs.slice(-MAX_LOGS + 1), data]` (single copy retained but bounded — O(cap) per message, constant memory). Show "older lines dropped" affordance in `EvaluationLogPanel` when at cap.
2. Optional micro-batch: accumulate messages in a `pendingLogs` ref flushed via `requestAnimationFrame` — only if profiling still shows jank after capping (don't gold-plate).

## Alternatives considered
Virtualized log list (react-window) — solves render cost but not memory; the cap alone meets the realistic need (users scan recent lines; full logs belong in artifacts).

## Verification
`evaluationStore.test.ts`: push 1,000 log messages → `logs.length === 500`, first entry is message 501. Manual: 500-item run scrolls smoothly.

## Relationship notes
- `related: FE-001` — same store; FE-001 changes how the connection starts, not the buffer; independent.
