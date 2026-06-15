---
id: CONS-006
title: Log event naming mixes dot-namespaced events, snake_case events, and prose sentences
category: consistency
severity: trivial
effort: S
confidence: high
breaking: false
status: open
depends_on: []
blocks: []
supersedes: []
superseded_by: []
conflicts_with: []
related: []
child_of: null
affected_paths:
  - backend/app/api/v1/providers.py
  - backend/app/api/v1/evaluators.py
  - backend/app/core/registry_base.py
  - backend/app/core/subprocess_validation.py
---

## Problem
structlog event names follow three conventions: `domain.action` dot-namespacing (the majority: `evaluation.created`, `mcp.starting`), bare snake_case (`config_file_uploaded`, `skipping_non_dict_entry`, `adapter_not_importable`), and full prose sentences (`"failed to fetch models from provider"`). Log filtering/searching by prefix is therefore unreliable.

## Evidence
- Dot style (dominant): `api/v1/evaluations.py:66` (`evaluation.created`), `services/agent_chat_service.py:166` (`agent_chat.llm_call`), `mcp/client.py:177`.
- Snake style: `api/v1/evaluators.py:154` (`config_file_uploaded`), `core/registry_base.py:80` (`skipping_non_dict_entry`), `:96` (`config_file_deleted` — which also collides semantically with evaluators.py's `config_file_deleted` at `:210` meaning a different thing), `core/subprocess_validation.py:86`.
- Prose: `api/v1/providers.py:288` (`"failed to fetch models from provider"`).

## Impact
Cosmetic but real: dashboards/grep can't rely on `domain.` prefixes; one literal name collision exists with two meanings (registry file deletion vs uploaded-config deletion).

## Root cause
No stated convention.

## Proposed fix (specification)
1. Document the rule in CLAUDE.md (one line): `logger events are "<domain>.<action>" lowercase`.
2. Rename the ~12 outliers (registry_base → `registry.entry_skipped`, `registry.config_changed`, `registry.config_deleted`, `registry.write_failed`; evaluators.py → `evaluator_config.uploaded/deleted`; subprocess_validation → `subprocess.allowlist_entry_unresolvable`; providers.py:288 → `provider.models_fetch_failed`).
3. No log-consumer migration needed (nothing parses these yet — that's the point of doing it now).

## Alternatives considered
Do nothing — reasonable; filed as trivial because the collision and prose event are genuinely confusing in mixed output.

## Verification
`grep -rn 'logger\.\(info\|warning\|error\|exception\)("' backend/app | grep -v '\."' | grep -vE '"\w+\.\w+"'` → empty (all events dot-namespaced).

## Relationship notes
None — standalone cosmetic sweep; batch into the quick-wins PR.
