---
id: SIMP-007
title: examples/judges YAML files are consumed by nothing and describe a panel judge that doesn't exist
category: simplification
severity: low
effort: XS
confidence: high
breaking: false
status: open
depends_on: []
blocks: []
supersedes: [DOC-004]
superseded_by: []
conflicts_with: []
related: [DATA-005, DOC-001]
child_of: null
affected_paths:
  - examples/judges/panel-judge.yaml
  - examples/judges/standard-judge.yaml
---

## Problem
No code loads judge YAML files (judges are DB rows via `/api/v1/judges`; there is no import endpoint or file loader for this format). `panel-judge.yaml` describes a three-model `majority_vote` panel — no panel implementation exists anywhere (CLAUDE.md's `judges/panel.py` is fictional). Worse, both files' `prompt_template` instructs the judge to return `{"correctness", "completeness", "helpfulness"}` JSON, while the only consumer of custom templates (`evaluate_qa`) parses `result.get("score", 0.0)` — a user who pastes these templates gets silent 0.0 scores.

## Evidence
- No loader: `grep -rn "examples/judges\|panel" backend/app --include="*.py"` → nothing; judges API is plain CRUD (`api/v1/judges.py`).
- Panel vapor: `examples/judges/panel-judge.yaml:11-22` (`aggregation: majority_vote`, `panel:` list).
- Template/parser mismatch: `examples/judges/standard-judge.yaml:25-26` (JSON without `score`) vs `backend/app/adapters/litellm_judge.py:200` (`float(result.get("score", 0.0))`).

## Impact
Examples are the first thing users copy; these either do nothing (no loader) or actively break scoring (template shape). The panel file advertises a capability that doesn't exist.

## Root cause
Examples written against the originally planned judge architecture (single/panel) that was never built.

## Proposed fix (specification)
1. DELETE `examples/judges/panel-judge.yaml` and `examples/judges/standard-judge.yaml` (and the `examples/judges/` dir).
2. If a worked example is wanted, replace with one `curl` snippet in `docs/docs/api-reference.md` creating a judge config whose `prompt_template` emits `{"score": <float>, "reasoning": "..."}` — matching the parser.
3. Sample datasets in `examples/datasets/` are genuinely useful for the import flow — keep.

## Alternatives considered
Fix the templates in place — rejected: still no loader consumes the files; corrected dead files are still dead.

## Verification
`grep -rn "panel-judge\|standard-judge" . --exclude-dir=review` → nothing; docs build green.

## Relationship notes
- `supersedes: DOC-004` — DOC-004 records the misleading-example problem; deletion resolves it without action.
- `related: DATA-005` — the judge/rubric consolidation defines what a real example should look like afterwards.
- `related: DOC-001` — CLAUDE.md's `examples/judges/ # Judge configuration templates` line updates with the tree fix.
