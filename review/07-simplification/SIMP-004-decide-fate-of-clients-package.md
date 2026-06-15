---
id: SIMP-004
title: Delete the clients/ SDK+CLI package (or commit to CI-testing it) — currently an untested third API mirror
category: simplification
severity: medium
effort: M
confidence: high
breaking: true
status: open
depends_on: []
blocks: []
supersedes: []
superseded_by: []
conflicts_with: [INFRA-005]
related: [ARCH-004, DOC-003]
child_of: null
affected_paths:
  - clients/
  - docs/docs/ci-cd-integration.md
---

## Problem
`clients/` is a complete hand-written Python SDK (sync **and** async variants of every namespace) plus a Typer CLI — 27 source/test files with their own pyproject and lockfile. It re-declares the API's models (third mirror after backend schemas and FE types), duplicates itself internally (sync/async twins), and is exercised by **no CI job**, so it drifts silently. Its one documented consumer is the `docs/ci-cd-integration.md` guide.

## Evidence
- Package scope: `clients/src/eval_studio/{client.py,async_client.py,models.py,_http.py,config.py,exceptions.py,cli/*}` + 8 test files; own `pyproject.toml`/`uv.lock`.
- Sync/async twins: `client.py` vs `async_client.py` implement the same namespaces twice.
- Not in CI: `.github/workflows/ci.yml` jobs are lint (backend+frontend), test-backend, test-frontend, container-smoke — no `clients/` step.
- The CLI's core use case is already served one level down: `POST /api/v1/evaluations/run` with `Accept: text/plain` returns `score\nVERDICT` exactly for shell pipelines (`backend/app/api/v1/evaluations.py:143-254`).

## Impact
Three hand-maintained type mirrors; an entire sub-project that can break without any signal; reviewer surface for every API change. Whatever choice is made, the current state (shipped but untested) is the worst option.

## Root cause
SDK built in anticipation of CI-pipeline users; CI integration for the package itself never followed.

## Proposed fix (specification)
Recommended: **delete**.
1. DELETE the `clients/` directory entirely.
2. Rewrite `docs/docs/ci-cd-integration.md` around the run-and-wait endpoint (`curl -s -X POST …/evaluations/run -H 'Accept: text/plain'`; the 418-line guide likely already shows the HTTP flow — keep those parts, drop SDK/CLI sections) and exit-code handling via the returned verdict.
3. Remove any README/CLAUDE.md references to the SDK/CLI.
Estimated deletion ≈ 2,500 lines + a lockfile.
If the team instead wants the SDK (a real product decision): implement INFRA-005 (CI job: `cd clients && uv sync && uv run pytest`), regenerate `models.py` from OpenAPI per ARCH-004 step 4, and collapse the sync client into a thin wrapper over the async one. Exactly one of SIMP-004 / INFRA-005 may be implemented.

## Alternatives considered
Keep + test + generate (the INFRA-005 path) — legitimate if CI-pipeline adoption is a near-term goal; rejected as the default because the curl-able run endpoint already covers the documented use case with zero maintenance.

## Verification
- Delete path: repo grep for `eval_studio` (import name) and `eval-studio-client` → no hits outside review/; docs build (`make docs-build`) green; ci-cd guide commands verified against a running backend.

## Relationship notes
- `conflicts_with: INFRA-005` — opposite resolutions of "clients/ is untested"; ROADMAP recommendation: this issue wins.
- `related: ARCH-004` — if INFRA-005 wins instead, the models file must come from codegen, not hands.
- `related: DOC-003` — ci-cd-integration.md rewrite overlaps the docs-accuracy sweep.
