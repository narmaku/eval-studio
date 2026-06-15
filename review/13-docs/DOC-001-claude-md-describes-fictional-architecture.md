---
id: DOC-001
title: CLAUDE.md describes a fictional architecture — wrong directory tree, nonexistent modules, wrong WS routes, stale env vars
category: docs
severity: high
effort: S
confidence: high
breaking: false
status: open
depends_on: []
blocks: []
supersedes: []
superseded_by: []
conflicts_with: []
related: [CONS-001, SIMP-001, SIMP-002, SIMP-004, INFRA-003, DOC-002]
child_of: null
affected_paths:
  - CLAUDE.md
---

## Problem
CLAUDE.md — explicitly authoritative for both human contributors and AI agents ("These instructions OVERRIDE any default behavior") — describes a codebase that doesn't exist. An agent following it will look for files that aren't there, miss half the real packages, use a wrong WebSocket route, and set environment variables that do nothing. Per this review's own ground rules, a wrong CLAUDE.md actively poisons future work and is high severity.

## Evidence
Falsehoods (each checked against the tree):
- Directory tree lists `backend/app/adapters/{qa.py,rag.py,agent.py,comparison.py}`, `judges/{base,single,panel}.py`, `environments/{compose.py,tmt.py}` — none exist; real packages `agent_backends/`, `rag_backends/`, `harnesses/`, `mcp/`, and 9 of the 15 actual routers (providers, rubrics, sessions, artifacts, api_keys, evaluators, harnesses, tool_servers, dataset_import) are absent from the tree. Top-level `clients/` and `config/` missing entirely.
- "WebSocket endpoints: `/ws/chat/{session_id}`" — actual route is `/ws/session/{session_id}` (`backend/app/websocket/chat.py:56`).
- "All LLM calls go through LiteLLM — never import provider SDKs directly… switching by changing `LITELLM_MODEL` and `LITELLM_API_KEY`" — the custom httpx adapter calls endpoints directly by design, and `LITELLM_MODEL` is not a setting (CONS-001).
- "Adding a New Evaluation Adapter… register in the adapter registry" — the registry dispatch is dead (BUG-018/SIMP-002).
- Workflow "Add the router to the FastAPI app in main.py" — fine; but "tests in `backend/tests/unit/test_<name>_adapter.py`" naming matches only some files.
- Tree claims `examples/judges/ # Judge configuration templates` consumed by a judge system that doesn't load them (SIMP-007).
- No mention of `dev.sh` (INFRA-003) or the migration prerequisite (DOC-002/INFRA-002).

## Impact
Every AI-agent session and new contributor starts from systematically wrong premises; time is spent hunting `qa.py`/`panel.py`; instructions cause real misconfiguration (`LITELLM_MODEL`).

## Root cause
CLAUDE.md was written as a design document before implementation, then never reconciled as the implementation diverged.

## Proposed fix (specification)
Rewrite the factual sections after the Phase-1 structural decisions land (so it documents the end-state once, not twice):
1. Replace the directory tree with the real one (generate from `find backend/app frontend/src -maxdepth 2 -type d` and annotate; keep it shallow — deep trees rot fastest).
2. Fix: WS routes (`/ws/session/{id}`, `/ws/progress/{id}`); LLM-access paragraph (LiteLLM for litellm-type providers, raw httpx for `custom` providers + RAG endpoints); env var names per CONS-001's decision; DB section gains the auto-migration behavior (INFRA-002).
3. Rewrite "Development Workflows" to match surviving subsystems (drop adapter-registry workflow if SIMP-002 lands; drop environment-provider workflow with SIMP-001; adjust if BUG-018 wins instead).
4. Add the two genuinely missing operational facts contributors need: the single dev launcher (INFRA-003 outcome) and the registry/YAML config model.
5. Keep the good parts verbatim (pitfalls 1–8 are accurate and valuable — verify each still holds at rewrite time).

## Alternatives considered
Patch only the worst lines now and fully rewrite later — acceptable interim (fix the WS route + LITELLM_MODEL + tree at minimum), but schedule the real rewrite; half-true docs invite half-trust.

## Verification
A checklist pass: every path mentioned in CLAUDE.md exists (`grep -oE 'backend/[a-zA-Z0-9_/.]+' CLAUDE.md | xargs -I{} test -e {}` style script); every command runs; every env var appears in Settings or the registry list.

## Relationship notes
- `related: SIMP-001, SIMP-002, SIMP-004` — their outcomes determine what the rewrite says; sequence the full rewrite after them (interim patch can go anytime).
- `related: CONS-001, INFRA-003, DOC-002` — supply the corrected env/launcher/setup facts.
