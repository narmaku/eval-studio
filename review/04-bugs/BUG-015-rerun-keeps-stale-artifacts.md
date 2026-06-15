---
id: BUG-015
title: Re-running an evaluation deletes old results but keeps old artifacts, accumulating stale files
category: bugs
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
related: [ARCH-001, PERF-004]
child_of: null
affected_paths:
  - backend/app/api/v1/evaluations.py
  - backend/app/services/artifact_generation.py
---

## Problem
`POST /{id}/rerun` clears the evaluation's `Result` rows but not its `Artifact` rows or files; each completed run then appends three more artifacts (results.json, summary.md, config.json). After N reruns the artifacts list shows 3·N entries whose names are identical, and all but the latest three describe deleted results.

## Evidence
- Rerun deletes results only: `backend/app/api/v1/evaluations.py:350-359`.
- Artifact generation appends per run: `services/artifact_generation.py:27-60` (no replacement logic; `save_artifact` always creates a new uuid-prefixed file, `artifact_service.py:101-103`).
- FE lists them all: `GET /artifacts?evaluation_id=…` ordered by created_at (`api/v1/artifacts.py:39`).

## Impact
UI confusion (which results.json is current?), unbounded disk growth per rerun, artifacts that contradict the database.

## Root cause
Artifact feature added after rerun; cleanup never wired.

## Proposed fix (specification)
In the rerun endpoint, alongside result deletion: fetch `Artifact` rows for the evaluation, call `delete_artifact_file` for each, delete the rows (mirror the delete-evaluation cascade semantics; evaluation deletion already cascades rows via `models/evaluation.py:30-32` — note it does NOT delete files either; include file deletion for the cascade path by handling it in `delete_evaluation` too, `api/v1/evaluations.py:274-288`).

## Alternatives considered
Versioned artifacts (keep history per run) — only worth it with a run-history model; current data model has one results set per evaluation, so artifacts should match it.

## Verification
Integration: run → rerun → `GET /artifacts?evaluation_id` returns exactly 3 entries; files on disk for the old uuids are gone. Also: delete evaluation → artifact files removed from disk.

## Relationship notes
- `related: ARCH-001` — rerun endpoint is being touched there; combine.
- `related: PERF-004` — same endpoint's row-by-row result deletion.
