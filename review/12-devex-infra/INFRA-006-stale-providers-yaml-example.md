---
id: INFRA-006
title: providers.yaml.example uses field names the parser no longer reads (litellm_model, purpose)
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
conflicts_with: []
related: [CONS-001, BUG-007]
child_of: null
affected_paths:
  - config/providers.yaml.example
---

## Problem
The example file users are told to copy ("Copy this file to providers.yaml and customize") defines providers with `litellm_model:` and `purpose:` keys. The parser reads `default_model` (the field was renamed) and has no `purpose` concept (deliberately dropped). Copying the example verbatim yields three providers with **empty** `default_model` — which the `single_model` heuristic then silently flags as single-model endpoints (`not raw.get("default_model","")` → `True`), making the UI hide model selection for what are actually normal multi-model providers.

## Evidence
- Stale keys: `config/providers.yaml.example:8,11,15,18,23,25`.
- Parser fields: `backend/app/core/providers.py:46-65` (`default_model` at `:50`; no `purpose`); heuristic at `:62`.
- The renames happened: migration `416da1255d27_rename_litellm_model_to_default_model.py`, `a3b4c5d6e7f8_drop_purpose_from_providers.py` (same rename applied to the YAML dataclass, example never updated).

## Impact
The blessed onboarding path for configuring providers produces broken provider entries with confusing downstream behavior (no model set, single-model UI mode) and no error — `extra` keys are silently ignored.

## Root cause
Field renames applied to code and DB migrations but not to the example artifact.

## Proposed fix (specification)
Rewrite the example with current fields:
```yaml
providers:
  - id: openai-gpt4
    name: "OpenAI GPT-4.1"
    default_model: "gpt-4.1"
    api_key_env: "OPENAI_API_KEY"
    tags: ["openai"]

  - id: ollama-local
    name: "Local Ollama"
    default_model: "ollama/llama3.2:3b"
    api_base: "http://localhost:11434"
    tags: ["local", "dev", "free"]
```
(Drop the redundant third "judge" entry — any provider can judge, per `api/v1/judges.py:79-81`; or keep it with a comment saying exactly that.) Optionally add one commented-out `provider_type: custom` example showing `endpoint_url`/`request_body_template`.

## Alternatives considered
Parser-side aliases for old keys — rejected: the example is the bug, not the parser.

## Verification
`cp config/providers.yaml.example config/providers.yaml`, start backend → `GET /api/v1/providers` shows both entries with correct `default_model`, `single_model: false`.

## Relationship notes
- `related: CONS-001` — sibling stale-contract problem in `.env.example`; same rename event is the root of both.
- `related: BUG-007` — the `single_model` heuristic interplay that amplifies this example's damage.
