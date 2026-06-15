---
id: CONS-005
title: 422 validation errors stringify Pydantic's error list into the RFC7807 detail field
category: consistency
severity: low
effort: XS
confidence: high
breaking: true
status: open
depends_on: []
blocks: []
supersedes: []
superseded_by: []
conflicts_with: []
related: [ARCH-004]
child_of: null
affected_paths:
  - backend/app/main.py
  - backend/app/schemas/common.py
---

## Problem
The custom `RequestValidationError` handler flattens Pydantic's structured error list into `detail=str(exc.errors())` — a Python-repr string (single quotes, `ValueError(...)` reprs) inside an otherwise clean RFC 7807 envelope. Clients can't programmatically tell which field failed, and the FE just displays the repr.

## Evidence
`backend/app/main.py:117-128`, specifically `detail=str(exc.errors())` at `:125`. `ProblemDetail` (`schemas/common.py:18-25`) has no field for structured errors.

## Impact
Field-level form validation in the FE is impossible (it shows a repr blob); the error contract is RFC 7807 in name but not in spirit for the most common error class.

## Root cause
Handler written to force every error through `ProblemDetail` without extending the model.

## Proposed fix (specification)
1. Add `errors: list[dict] | None = None` to `ProblemDetail` (RFC 7807 permits extension members).
2. Handler: `detail="Request validation failed"`, `errors=[{"loc": list(e["loc"]), "msg": e["msg"], "type": e["type"]} for e in exc.errors()]` (drop non-serializable `ctx`/`input` values or pass through `jsonable_encoder`).
3. FE `ApiError` type gains optional `errors`; forms may use it later (no immediate FE work required).

## Alternatives considered
Delete the custom handler and use FastAPI's default 422 — rejected: loses envelope uniformity that the FE error path already relies on.

## Verification
`uv run pytest tests/integration/test_evaluations.py -k validation` (or add one: POST /evaluations with missing name → assert `errors[0].loc == ["body","name"]`).

## Relationship notes
- `related: ARCH-004` — the extended ProblemDetail flows into generated FE types.
