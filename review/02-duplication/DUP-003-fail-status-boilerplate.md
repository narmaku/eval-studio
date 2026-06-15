---
id: DUP-003
title: Fail-status boilerplate (set failed → commit → broadcast) repeated 12× across eval services
category: duplication
severity: medium
effort: S
confidence: high
breaking: false
status: open
depends_on: []
blocks: []
supersedes: []
superseded_by: [ARCH-001]
conflicts_with: []
related: []
child_of: ARCH-001
affected_paths:
  - backend/app/services/evaluation_service.py
  - backend/app/services/arena_evaluation_service.py
  - backend/app/services/rag_evaluation_service.py
---

## Problem
The four-line early-exit ritual — `evaluation.status = "failed"; evaluation.error = …; await db.commit(); await broadcast_status(...); return` — appears twelve times across the three batch evaluation services.

## Evidence
`evaluation_service.py:48-52, 58-62, 75-79, 98-102, 129-133`; `arena_evaluation_service.py:50-54, 60-64, 76-80, 93-97, 106-110, 162-168`; `rag_evaluation_service.py:85-89, 95-99, 112-116, 128-133, 144-149` (overlapping enumerations; 12 distinct sites).

## Impact
Any change to failure semantics (e.g. also broadcasting a log entry, or recording `failed_at`) needs a dozen edits; one site already differs subtly (arena's resolved-contestant failure composes its message differently).

## Root cause
Symptom of the service triplication (ARCH-001).

## Proposed fix (specification)
None standalone — ARCH-001's single `fail(evaluation, db, detail)` helper removes all twelve sites. If ARCH-001 were rejected, extract the helper into a shared module and call it from all three services.

## Alternatives considered
Standalone helper extraction without ARCH-001 — workable but pointless churn if the consolidation lands.

## Verification
Covered by ARCH-001's verification; additionally `grep -c 'status = "failed"' backend/app/services/*.py` drops to the single helper.

## Relationship notes
- `superseded_by: ARCH-001` / `child_of: ARCH-001` — this is a symptom record; close without action when ARCH-001 lands.
