---
id: CONS-002
title: Status/mode values are raw string literals across backend despite existing enums
category: consistency
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
related: [API-004, DUP-004, ARCH-001]
child_of: null
affected_paths:
  - backend/app/schemas/evaluation.py
  - backend/app/services/evaluation_service.py
  - backend/app/services/arena_evaluation_service.py
  - backend/app/services/rag_evaluation_service.py
  - backend/app/services/agent_chat_service.py
  - backend/app/api/v1/evaluations.py
  - backend/app/api/v1/sessions.py
  - backend/app/models/session.py
---

## Problem
`EvaluationMode` and `EvaluationStatus` StrEnums exist (`schemas/evaluation.py:8-20`) but nearly all comparisons and assignments use raw strings; session statuses (`active/ended/scoring/completed`) have no enum at all. SQLite columns carry no CHECK constraints, so a typo'd status would persist silently.

## Evidence
- Assignments/comparisons with literals: `evaluation_service.py:37,42,48,294,297`; `api/v1/evaluations.py:302,308,312,345,348,357`; `agent_chat_service.py:84-85,567,575`; `api/v1/sessions.py:124,152,155,184,188,236,269`.
- Session model default uses bare strings: `models/session.py:18-19`.
- The enums are used only at API boundaries (`api/v1/evaluations.py:74-87`, `run_service.py:100-101`).
- No `SessionStatus`/`SessionMode` enum exists anywhere in `backend/app/schemas/session.py` (FE has one: `frontend/src/types/session.ts:4-5`).

## Impact
Refactors (rename a status, add one) can't be found by the type checker; FE and BE enumerate different value sets today (API-004); the `"scoring"` transient status exists only as scattered literals.

## Root cause
Enums added to schemas late; services were already written with literals.

## Proposed fix (specification)
1. Add `SessionStatus(StrEnum)` (`active`, `ended`, `scoring`, `completed`) and `SessionMode(StrEnum)` (`live`, `simulated`) to `backend/app/schemas/session.py`.
2. Replace literal comparisons/assignments with enum members across the files listed (StrEnum values compare equal to their strings, so this is mechanically safe and DB values are unchanged).
3. Keep ORM columns as `String` but set defaults from the enums (`default=SessionStatus.ACTIVE`).
4. Resolve the `cancelled` member per API-004 (it is currently a lie); do not blindly port it.

## Alternatives considered
DB-level CHECK constraints — nice-to-have; deferred to keep migration churn down (note in DATA-006 if a squash happens).

## Verification
`grep -rnE '"(pending|running|completed|failed|active|ended|scoring)"' backend/app --include="*.py" | grep -v schemas/` shrinks to ~0 (string literals only inside enum definitions and tests); `uv run pytest` green.

## Relationship notes
- `related: API-004` — decides which status values exist at all; do API-004's decision first or together so the enums codify the truth.
- `related: DUP-004, ARCH-001` — the consolidation rewrites several of the listed sites; applying enums during ARCH-001 avoids double edits.
