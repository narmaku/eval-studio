---
id: INFRA-005
title: clients/ has a full test suite that no CI job ever runs
category: devex-infra
severity: medium
effort: XS
confidence: high
breaking: false
status: open
depends_on: []
blocks: []
supersedes: []
superseded_by: []
conflicts_with: [SIMP-004]
related: [ARCH-004]
child_of: null
affected_paths:
  - .github/workflows/ci.yml
  - clients/
---

## Problem
The `clients/` package ships 8 test modules and its own toolchain config, but `ci.yml` contains no job that installs or tests it — the SDK/CLI can break (and drift from the API) with zero signal.

## Evidence
- `.github/workflows/ci.yml` jobs: lint (backend+frontend, `:13-45`), test-backend (`:47-66`), test-frontend (`:68-84`), container-smoke (`:86-118`) — no `clients` reference anywhere in `.github/`.
- Test suite exists: `clients/tests/` (test_client, test_async_client, test_cli, test_config, test_models, test_exceptions, test_cli_output, conftest).

## Impact
A shipped, documented package (docs/ci-cd-integration.md) with guaranteed-eventual rot; reviewers reasonably assume CI covers it.

## Root cause
CI written for the two main tiers; the sub-package was added without extending it.

## Proposed fix (specification)
**Conditional on SIMP-004's resolution** — exactly one of the two issues may be implemented:
- If clients/ is kept: add a CI job mirroring test-backend:
  ```yaml
  test-clients:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/setup-uv@v4
        with: { enable-cache: true }
      - working-directory: clients
        run: |
          uv sync --quiet --all-extras
          uv run ruff check .
          uv run pytest -q
  ```
- If SIMP-004 deletes clients/: this issue closes without action.

## Alternatives considered
N/A — the conflict pair covers the option space.

## Verification
CI run shows the new job green; intentionally break a client model field locally → job fails.

## Relationship notes
- `conflicts_with: SIMP-004` — keep-and-test vs delete; ROADMAP recommends SIMP-004 (delete), in which case close this as superseded-in-effect.
- `related: ARCH-004` — if kept, models should be generated, making the CI job's drift detection real.
