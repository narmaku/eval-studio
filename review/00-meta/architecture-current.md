# Architecture As-Is (honest description)

This is what the system actually is today, including the accidental parts. The documented architecture (CLAUDE.md, docs/) describes a different, partly fictional system — see DOC-001.

## The real shape

eval-studio is a **single-process FastAPI monolith + React SPA** for running LLM evaluations locally. Everything meaningful happens in `backend/app/services/`; there is no domain layer. State lives in three places simultaneously: SQLite (entities + results), YAML files in `config/` (providers, harnesses, tool servers — mutated at runtime by the API), and process memory (import sessions, WS connection maps, MCP managers, background task refs). This three-way split is the single largest source of accidental complexity.

## Layering

- API routers are mostly thin and consistent (load → validate → mutate → respond), with two exceptions: `sessions.py:score_session` contains a full scoring pipeline inline, and `evaluators.py` embeds a small file-management subsystem.
- "Services" are not a layer with a contract; they are four parallel orchestration scripts (qa/arena/rag/agent-chat) that each re-implement the same lifecycle: load evaluation → set running → load dataset/judge → resolve models → fan out with a semaphore → collect → set completed/failed → broadcast → generate artifacts. The qa/arena/rag triplet is ~85% identical code.
- Cross-cutting concerns (status transitions, error broadcast, artifact generation) are copy-pasted, not shared.

## The plugin systems (five of them)

The codebase contains five separate plugin/registry mechanisms, four of which have exactly one or zero real implementations:

1. **Evaluation adapters** (`adapters/`): ABC + YAML registry + dynamic import + namespace allowlist + factory → exactly one adapter (`LiteLLMJudgeAdapter`). The factory is only ever called with its default. The frontend lets users pick an evaluator and sends `config.evaluator_id`; **no backend code reads it**.
2. **Agent backends** (`agent_backends/`): ABC + factory → two real implementations (litellm streaming, custom httpx). This one earns its keep.
3. **RAG backends** (`rag_backends/`): ABC + factory → two implementations (http, pgvector). Borderline-earns its keep.
4. **Harnesses** (`harnesses/`): ABC + YAML registry + factory → one real implementation (subprocess); `BuiltinHarness` exists only so the factory can instantiate it and says so in its docstring; the builtin path bypasses the harness abstraction entirely inside `agent_chat_service`.
5. **Environment providers** (`environments/`): ABC + one stub (BYOE, all TODOs). The REST API for environments is six endpoints that all raise 501. CLAUDE.md/docs describe Compose and TMT providers that do not exist.

## Providers: two sources of truth

Provider profiles live in the YAML registry (`core/providers.py`, CRUD via `/api/v1/providers`). A parallel SQLAlchemy `Provider` table exists with ~6 migrations of history, an in-lifespan raw-SQL data migration, and a converter function (`resolve_provider`) that no code calls. The DB side is dead weight that still shapes the mental model and the migration chain.

## Contract management

Backend Pydantic schemas, frontend TS types (`src/types/`), and `clients/` Pydantic models are three hand-maintained mirrors of the same API. Drift exists today (rubrics pagination params, session replay/import response types, WS chat envelope `message_id`, phantom statuses `cancelled`/`failed`). OpenAPI is exposed at `/api/v1/openapi.json` but nothing generates from it.

## Real-time design

Two WS endpoints with module-level connection maps. Progress WS is broadcast-only with no replay buffer — the FE compensates with a 200 ms sleep before starting a run and re-uses POST `/rerun` to start first runs. Chat WS has a hand-rolled envelope protocol duplicated (and drifted) on each side. Neither endpoint enforces auth or checks origins.

## Configuration

Two mechanisms: pydantic-settings (`Settings`, reads repo-root `.env`) and direct `os.environ` reads inside the four registries (`*_CONFIG_PATH`) plus `api_key_env` indirection. `.env.example` documents variables the Settings class doesn't have (`LITELLM_MODEL`, `LITELLM_API_BASE`, registry paths) and a "planned/future" section of pure vapor.

## Deployment reality

- Dev works via `make dev` or `dev.sh` (two divergent launchers), **provided the user has manually run `alembic upgrade head`** — no path creates the schema automatically, and the lifespan's raw `UPDATE sessions/providers` statements run against whatever DB exists.
- Prod (`Containerfile` + nginx) builds the frontend into `/app/static/` and then never serves it: the backend mounts no static files and nginx proxies `/` to the backend. The shipped production image has no working UI. CI's container smoke test only curls `/api/v1/health`, so this is invisible.

## What is genuinely good

- Consistent async SQLAlchemy 2.0 style (`select()` + `Mapped`), one session-per-request dependency, WAL pragma.
- RFC 7807 error envelope with a sanitization helper used fairly consistently on the WS/HTTP error paths.
- Subprocess allowlisting (`subprocess_validation`) applied to both harnesses and MCP servers; artifact path traversal defenses; artifact preview XSS hardening.
- structlog with correlation IDs.
- A real test suite (≈75 backend test files, FE store/component tests) that is mostly meaningful, not mock theater.
