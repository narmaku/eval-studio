---
id: BUG-009
title: HttpRAGAdapter's shared httpx client is never closed by the RAG evaluation service
category: bugs
severity: low
effort: XS
confidence: high
breaking: false
status: done
depends_on: []
blocks: []
supersedes: []
superseded_by: []
conflicts_with: []
related: [ARCH-001]
child_of: null
affected_paths:
  - backend/app/services/rag_evaluation_service.py
  - backend/app/rag_backends/http_adapter.py
---

## Problem
`HttpRAGAdapter` lazily creates a shared `httpx.AsyncClient` and provides a `close()` method, but `run_rag_evaluation` never calls it — each RAG run leaks one client (open connection pool) for the life of the process.

## Evidence
- Client creation + close method: `backend/app/rag_backends/http_adapter.py:36-42, 73-77`.
- Adapter created at `services/rag_evaluation_service.py:136`; `grep -n "close" backend/app/services/rag_evaluation_service.py` → nothing; no `finally` around the run body relates to the adapter.

## Impact
Slow leak of sockets/FDs proportional to RAG runs; harmless at toy scale, real on a long-lived server. Also sets a bad example: the class advertises a lifecycle nobody drives.

## Root cause
Adapter extracted from inline code ("Refactored from inline httpx code", `http_adapter.py:4-5`) gained a client lifecycle without the caller adopting it.

## Proposed fix (specification)
1. In `run_rag_evaluation`, wrap the per-item processing in `try/finally: await rag_adapter.close()` — add `close()` as a no-op default on `RAGBackendAdapter` (`rag_backends/base.py`) so pgvector needs nothing.
2. Post-ARCH-001: `RAGRunner.run_item`'s owner closes the adapter in the runner's teardown (ARCH-001's spec step 2 already notes this).

## Alternatives considered
Per-request client (no shared state) — simpler but loses connection reuse across N dataset items; keep the shared client, fix the lifecycle.

## Verification
Unit: monkeypatch adapter with a close-spy in `tests/unit/test_rag_evaluation_service.py`; assert called on success and on failure paths.

## Relationship notes
- `related: ARCH-001` — the consolidation relocates the fix; the `finally` should be added now and carried over.
