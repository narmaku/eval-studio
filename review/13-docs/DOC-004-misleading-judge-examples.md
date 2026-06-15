---
id: DOC-004
title: examples/judges templates teach a response format the judge parser cannot score
category: docs
severity: low
effort: XS
confidence: high
breaking: false
status: open
depends_on: []
blocks: []
supersedes: []
superseded_by: [SIMP-007]
conflicts_with: []
related: []
child_of: SIMP-007
affected_paths:
  - examples/judges/standard-judge.yaml
  - examples/judges/panel-judge.yaml
---

## Problem
Both example judge files instruct the LLM to respond with `{"correctness": …, "completeness": …, "helpfulness": …}`, but the QA judge parser reads only `result.get("score", 0.0)` — a user adopting these templates gets every item scored 0.0 with no error. The panel example additionally documents a `panel`/`majority_vote` mechanism that exists nowhere in the codebase.

## Evidence
- `examples/judges/standard-judge.yaml:25-26`, `panel-judge.yaml:37-38` (JSON shape without `score`).
- Parser: `backend/app/adapters/litellm_judge.py:200` (`float(result.get("score", 0.0))`).
- Panel vapor: `panel-judge.yaml:11-22`; `grep -rn "majority_vote\|panel" backend/app --include="*.py"` → nothing.

## Impact
Examples that silently zero out scores are worse than no examples.

## Root cause
Written against the originally planned judges subsystem.

## Proposed fix (specification)
Symptom record — SIMP-007 deletes both files and replaces them with a parser-conformant snippet in the API reference. No standalone action unless SIMP-007 is rejected, in which case rewrite both templates to emit `{"score": <float>, "reasoning": "<…>"}` and delete the `panel:` block.

## Alternatives considered
N/A.

## Verification
Covered by SIMP-007.

## Relationship notes
- `superseded_by: SIMP-007` / `child_of: SIMP-007` — closes with the deletion.
