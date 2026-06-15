---
id: SEC-003
title: PgVector adapter interpolates user-supplied table/column names directly into SQL
category: security
severity: medium
effort: XS
confidence: high
breaking: false
status: open
depends_on: []
blocks: []
supersedes: []
superseded_by: []
conflicts_with: []
related: [SEC-004, SEC-001]
child_of: null
affected_paths:
  - backend/app/rag_backends/pgvector_adapter.py
---

## Problem
`table_name`, `embedding_column`, `content_column`, and `top_k` come from evaluation config (API-supplied) and are f-string-interpolated into the SQL text. A crafted `table_name` like `docs; DROP TABLE users; --` executes arbitrary statements on the connected PostgreSQL database.

## Evidence
- `backend/app/rag_backends/pgvector_adapter.py:66-72`:
  ```python
  query = (
      f"SELECT {self.content_column}, "
      f"1 - ({self.embedding_column} <=> $1::vector) as relevance "
      f"FROM {self.table_name} "
      ...
      f"LIMIT {self.top_k}"
  )
  ```
- Values flow from `rag_endpoint` config: `rag_backends/factory.py:34-39`, fed by `services/rag_evaluation_service.py:39-56`.

## Impact
Tempered by the trust model: the attacker must already control the evaluation config *and* the `connection_string` points at a database they chose — so in the single-user local posture they're "attacking" their own DB. It becomes a real privilege issue the moment the tool is shared (SEC-005) or a config is imported from someone else. Defense costs nearly nothing; carrying a textbook injection in the codebase costs more.

## Root cause
Identifiers can't be bound as parameters in SQL, and the easy f-string was taken without identifier validation.

## Proposed fix (specification)
1. Validate identifiers in `__init__`:
   ```python
   _IDENT = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
   for label, v in {"table_name": table_name, "embedding_column": embedding_column, "content_column": content_column}.items():
       if not _IDENT.match(v):
           raise ValueError(f"{label} must be a simple SQL identifier, got: {v!r}")
   ```
   (Schema-qualified names: allow one optional `.` by validating each part.)
2. Quote them in the query (`f'"{self.table_name}"'` after validation) and coerce `top_k = int(top_k)`.
3. `$1` embedding parameter is already bound correctly — no change.

## Alternatives considered
asyncpg `quote_ident` round-trip — fine too; the allowlist regex is simpler and also catches accidental garbage early with a good message.

## Verification
`tests/unit/test_pgvector_rag_adapter.py`: constructor rejects `table_name="docs; DROP"`; accepts `public.docs`; query string contains quoted identifiers.

## Relationship notes
- `related: SEC-004` — both are user-supplied-target concerns governed by the trust-model statement; this one keeps a concrete fix regardless of posture.
- `related: SEC-001` — `connection_string` exposure is handled there.
