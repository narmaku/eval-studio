---
id: API-003
title: FE response types lie for session replay and dataset import endpoints
category: api-contracts
severity: low
effort: XS
confidence: high
breaking: false
status: open
depends_on: []
blocks: []
supersedes: []
superseded_by: [ARCH-004]
conflicts_with: []
related: []
child_of: ARCH-004
affected_paths:
  - frontend/src/services/api.ts
---

## Problem
Two `api.ts` methods declare return types that don't match the backend: `getSessionReplay` claims `Session` but the endpoint returns a `SessionReplayResponse` (different shape: `messages`, `tool_calls`, `duration_seconds`; no `transcript`/`agent_config`); `importDataset` claims `Dataset` but the endpoint returns either a `DatasetDetailResponse` **or a list of them** in "separate" merge mode.

## Evidence
- `frontend/src/services/api.ts:140` (`request<Session>(…/replay)`) vs `backend/app/api/v1/sessions.py:275-302` (`SessionReplayResponse`).
- `api.ts:175-176` (`request<Dataset>('/api/v1/datasets/import')`) vs `backend/app/api/v1/dataset_import.py:168` (`response_model=DatasetDetailResponse | list[DatasetDetailResponse]`).

## Impact
TypeScript actively misleads at these call sites; the separate-mode array case would throw at runtime in any consumer that trusts the type (`SmartImportDialog` must already special-case or be subtly wrong).

## Root cause
Hand-mirrored types (ARCH-004).

## Proposed fix (specification)
Closed by ARCH-004's generated types (both become exact). Point fix if needed sooner: declare `SessionReplay` and `DatasetDetail | DatasetDetail[]` types by hand at the two sites.

## Alternatives considered
N/A.

## Verification
Post-ARCH-004: `tsc --noEmit` with generated types; the import dialog's handling of array responses gets an explicit test.

## Relationship notes
- `superseded_by: ARCH-004` / `child_of: ARCH-004` — fully resolved by type generation; closes with it.
