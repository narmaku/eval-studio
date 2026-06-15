---
id: CONS-008
title: react-hook-form + zod adopted by exactly one component; every other form is hand-rolled state
category: consistency
severity: low
effort: M
confidence: high
breaking: false
status: open
depends_on: []
blocks: []
supersedes: []
superseded_by: []
conflicts_with: []
related: [FE-004]
child_of: null
affected_paths:
  - frontend/src/components/datasets/DatasetUploadDialog.tsx
  - frontend/src/components/settings/ProviderForm.tsx
  - frontend/src/components/settings/ToolServerForm.tsx
  - frontend/src/components/settings/RubricBuilder.tsx
  - frontend/package.json
---

## Problem
The repo carries three form dependencies (`react-hook-form`, `@hookform/resolvers`, `zod`) that are imported by exactly one component; all other forms (provider form, tool-server form, rubric builder, import dialogs, judge config) are hand-rolled `useState` + manual validation. Two patterns for one concern, and the dependency cost is paid for a single dialog.

## Evidence
- `grep -rEn "from '(react-hook-form|@hookform/resolvers|zod)'" frontend/src` → only `components/datasets/DatasetUploadDialog.tsx:2-4`.
- Hand-rolled examples: `components/settings/ProviderForm.tsx` (largest form in the app, manual state), `ToolServerForm.tsx`, `RubricBuilder.tsx`, `components/evaluation/JudgeConfigPanel.tsx`.
- Deps declared: `frontend/package.json:21,36,46`.

## Impact
Contributors face two form idioms with no rule for which to use; bundle includes a form library for one dialog.

## Root cause
One component adopted the stack; the convention never spread or got reverted.

## Proposed fix (specification)
Pick one direction; recommended given current weight of code: **standardize on hand-rolled forms** (the existing majority) —
1. Rewrite `DatasetUploadDialog.tsx` with the same `useState` pattern as its siblings (its schema is 3 fields; ~30 lines).
2. DELETE `react-hook-form`, `@hookform/resolvers`, `zod` from `package.json`.
If, instead, complex validation is on the roadmap (ProviderForm is large), invert the recommendation and migrate the settings forms to react-hook-form — but then do migrate them; don't keep both. Record the decision in ROADMAP.

## Alternatives considered
Status quo — rejected: the single-use library is exactly the kind of incidental inconsistency that compounds.

## Verification
`npm test -- --run` green (`DatasetUploadDialog.test.tsx` updated); `npm run build` succeeds; `grep -rn "react-hook-form" frontend/src` empty (if direction A).

## Relationship notes
- `related: FE-004` — both are FE-pattern unification work; independent.
