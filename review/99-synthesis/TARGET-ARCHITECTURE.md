# Target Architecture

The simplest architecture that serves eval-studio's *actual current scope*: a single-trust-domain workspace where one team runs LLM evaluations (Q&A, RAG, arena, interactive agent) against configurable providers, with live progress and downloadable artifacts. Not its aspirational scope (multi-framework adapter marketplace, managed environments, multi-tenant deployments).

Every structural issue in `01-architecture/` and `07-simplification/` is consistent with this document; where an issue offers options (BUG-018 vs SIMP-002, SIMP-004 vs INFRA-005, API-004 A/B), the choice assumed here is recorded and re-stated in ROADMAP.md.

## Shape

One FastAPI process + SQLite + one React SPA, served same-origin in production (backend serves the built SPA; nginx optional in front). Background work stays `asyncio.create_task` in-process. **We explicitly accept**: single process, single writer, no queue, no horizontal scaling. SQLite + WAL is fine for this product until proven otherwise.

## State lives in exactly two places

1. **SQLite** — entities and run data: datasets(+items), evaluations, results, sessions, rubrics, artifacts(+files on disk), api_keys.
2. **YAML registries in `config/`** — operator-editable connection config: providers, harnesses, tool_servers. Mutated via API, hot-reloaded by mtime. (Rationale: git-diffable, portable, already the live path — ARCH-002.)

Gone: the DB `providers` table (ARCH-002), the `environments` table and vertical (SIMP-001), the `judge_configs` table (merged into rubrics — DATA-005), in-lifespan raw-SQL migrations (ARCH-008). Alembic chain squashed to one initial revision (DATA-006) and applied automatically at startup (INFRA-002).

## Proposed backend layout

```
backend/app/
├── main.py                  # app factory; migrations-on-startup; static SPA mount; routers
├── core/
│   ├── config.py            # ALL settings incl. registry paths (ARCH-005)
│   ├── database.py          # engine, Base, get_db, utcnow()
│   ├── exceptions.py        # AppException family + sanitize_error_for_client
│   ├── logging.py
│   ├── security.py          # REST + WS auth (SEC-002)
│   ├── registry.py          # YAMLBackedRegistry + shared path resolution + isolated() test seam
│   ├── rate_limiter.py
│   └── subprocess_validation.py
├── registries/              # the three registries (providers, harnesses, tool_servers)
├── models/                  # 7 ORM models (api_key, artifact, dataset, evaluation, result, rubric, session)
├── schemas/                 # Pydantic incl. ws_chat.py envelopes (ARCH-003); source of generated FE types (ARCH-004)
├── api/v1/                  # one router per resource; environments/evaluators routers deleted
├── services/
│   ├── eval_runner.py       # THE batch orchestrator + QARunner/ArenaRunner/RAGRunner (ARCH-001)
│   ├── agent_chat.py        # decomposed interactive loop (ARCH-007) + single end_session (ARCH-006)
│   ├── judge.py             # LiteLLMJudgeAdapter (renamed home; only scoring backend) + rubric-driven dimensions (DATA-005)
│   ├── dataset_import.py
│   ├── dataset_service.py   # shared dataset+items persistence (DUP-007)
│   ├── artifacts.py
│   ├── rubric_service.py
│   └── providers.py         # resolve_model_config / call_model / per-provider clients (BUG-011)
├── agent_backends/          # litellm streaming + custom httpx (2 real impls — keeps its factory)
├── rag_backends/            # http + pgvector (2 real impls — keeps its factory)
├── harnesses/               # subprocess harness + goose parser (BuiltinHarness deleted — SIMP-003)
├── mcp/                     # client + manager (idempotent start — BUG-002)
└── websocket/               # progress (with replay buffer — FE-001) + chat
```

Deleted outright (file by file — union of SIMP-001/002/003, ARCH-002): `app/environments/*`, `api/v1/environments.py`, `models/environment.py`, `schemas/environment.py`, `adapters/registry.py`, `adapters/factory.py`, `api/v1/evaluators.py`, `models/provider.py`, `harnesses/builtin.py`, `config/evaluators.yaml`, `examples/judges/*`, `environments/{compose,tmt,ansible,scenarios}/`, `clients/` (SIMP-004), 21 of 22 alembic revisions, dead tests (TEST-002).

## Module responsibility table

| Module | Owns | Must not |
|--------|------|----------|
| `api/v1/*` | request validation, auth, response shaping | contain business logic (score_session's inline pipeline moves to services) |
| `services/eval_runner.py` | the entire batch-run lifecycle, status CAS (BUG-016), fail() helper, artifact trigger | know transport (WS calls go through broadcast functions only) |
| `services/agent_chat.py` | agentic loop, transcript persistence (one helper), session end (one function) | be called by anything but the WS handler and sessions router |
| `services/judge.py` | judge prompts, JSON parsing, one `_ask_judge` (DUP-006), proxy/SSL via per-client (BUG-013/011) | read evaluation rows |
| `services/providers.py` | model resolution (raises on unresolvable — BUG-001), provider client cache | mutate os.environ except in the locked legacy fallback |
| `registries/*` | YAML CRUD + reload; parse errors skip entries (BUG-003) | reach into Settings-free os.environ (ARCH-005) |
| `websocket/*` | connection maps, replay buffer, auth handshake | business decisions (session ending delegates to services) |

## The one way to do each thing

- **Config**: pydantic `Settings` only; registries get paths from Settings; secrets only via `*_env` indirection (SEC-001); `.env.example` is the complete, true contract (CONS-001).
- **Errors**: raise `AppException` subclasses in routers/services; everything client-bound passes `sanitize_error_for_client` — including persisted error text (BUG-010); 422s carry structured `errors` (CONS-005).
- **Logging**: structlog, `domain.action` event names (CONS-006).
- **DB access**: async SQLAlchemy 2.0 `select()`; no eager-loading defaults on collections (PERF-001); timestamps via single `utcnow()` into `DateTime(timezone=True)` (DATA-003); enums for statuses (CONS-002); FKs everywhere (DATA-001).
- **API shape**: DB collections paginate with `PaginatedResponse`; bounded config collections return arrays — written rule (CONS-004).
- **FE data fetching**: the single generalized `request()` helper (DUP-008); types generated from OpenAPI (ARCH-004); WS envelopes from backend Pydantic models (ARCH-003).
- **FE state**: Zustand store per domain (keep), shared `useEvaluationRun` hook for run lifecycle (FE-004); hand-rolled forms as the single form idiom (CONS-008 recommendation).
- **Scoring config**: providers say *where/what model*; **rubrics** say *how to judge* (dimensions/threshold/template) and are actually wired into prompts (DATA-005); judge_configs and "presets" are gone (API-005).

## What we are NOT building yet (explicit non-goals)

- Environment provisioning (Compose/TMT/BYOE) — deleted until a consumer exists (SIMP-001).
- Pluggable evaluator frameworks — one judge implementation, constructed directly; a `dict` factory returns the day a second real backend (e.g. lightspeed-evaluation) actually lands (SIMP-002 over BUG-018).
- A Python SDK/CLI — the `Accept: text/plain` run endpoint is the CI integration surface (SIMP-004 over INFRA-005).
- Multi-process/queue/Postgres scaling, multi-tenancy, RBAC — single trust domain declared (SEC-004/005); API keys stay as the one optional boundary and become usable end-to-end (SEC-005).
- Panel judges, MLflow export, Testing Farm — removed from examples/env templates until designed (SIMP-007, CONS-001).

## Decisions this document locks (recorded for ROADMAP)

1. SIMP-002 over BUG-018 (delete evaluator selection rather than wire it).
2. SIMP-004 over INFRA-005 (delete clients/).
3. API-004 option A (implement real cancellation) — the UI demonstrably wants it and the task model makes it ~50 lines.
4. CONS-008: hand-rolled forms win; drop the react-hook-form trio.
5. CONS-004: keep the paginated/bare split as a written rule; fix only `/artifacts`.
