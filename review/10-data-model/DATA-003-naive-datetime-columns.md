---
id: DATA-003
title: All DateTime columns are timezone-naive while every default/assignment is timezone-aware UTC
category: data-model
severity: low
effort: S
confidence: high
breaking: false
status: open
depends_on: []
blocks: []
supersedes: []
superseded_by: []
conflicts_with: []
related: [DUP-001, DATA-006]
child_of: null
affected_paths:
  - backend/app/core/database.py
  - backend/app/models/
---

## Problem
Every `DateTime` column is declared without `timezone=True`, but all defaults and assignments produce aware `datetime.now(UTC)` values. SQLite strips the offset on write, so reads return naive datetimes that the code may compare against aware ones — `aware - naive` raises `TypeError`, and serialized timestamps lack offsets, leaving FE `new Date()` parsing to assume local time (UI shows times shifted by the viewer's UTC offset).

## Evidence
- Naive columns: `core/database.py:35` (`Base.created_at`), `models/evaluation.py:24,46`, `models/session.py:25-26`, `models/api_key.py:16`, etc. — `grep -rn "DateTime" backend/app/models backend/app/core/database.py` shows zero `timezone=True`.
- Aware values written: `core/database.py:27-28`, `core/security.py:102`, `agent_chat_service.py:568`, plus the seven `_utcnow` copies (DUP-001).
- Live mixed-comparison hazard: `api/v1/sessions.py:288-290` (`ended_at - started_at` — currently safe only because *both* come back naive from SQLite; any in-memory object not yet round-tripped is aware).

## Impact
Latent TypeErrors at aware/naive boundaries; FE renders session/evaluation times offset from reality for any non-UTC user (ISO strings without `Z`).

## Root cause
SQLAlchemy's `DateTime` default is naive; nobody opted in to `timezone=True`.

## Proposed fix (specification)
1. Declare once in `Base`/models: switch all `DateTime` to `DateTime(timezone=True)` (SQLite stores ISO strings with offset; round-trips aware).
2. Use the single `utcnow()` helper from DUP-001 everywhere.
3. Alembic migration via `batch_alter_table` for the column type changes (SQLite type affinity makes this near-cosmetic, but existing stored values gain no offset — accept legacy rows as UTC by convention; optional data fix appends `+00:00`).
4. Pydantic responses then emit `…+00:00`, fixing FE parsing with no FE change.

## Alternatives considered
Store naive-UTC consistently and add `Z` at the serialization layer — workable but spreads the convention across every response model; column-level truth is simpler.

## Verification
- Unit: round-trip an Evaluation; `created_at.tzinfo is not None`.
- API: `created_at` in responses ends with an offset; FE displays correct local time (manual spot check).

## Relationship notes
- `related: DUP-001` — single helper first makes this mechanical.
- `related: DATA-006` — fold column-type changes into a squash if one happens.
