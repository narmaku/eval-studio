# eval-studio — Development Guide

## Project Overview

eval-studio is a workspace for building, running, and improving AI evaluations.
It covers dataset creation, scoring metrics/rubrics, and telemetry integrations,
used seamlessly with evaluation systems onboarded into the platform. The first
integration target is lightspeed-evaluation.

Evaluation modes: Q&A benchmarks, RAG evaluation, interactive agent sessions, and
side-by-side model arena.

## Development Mode

This project is in **fast-development mode** (pre-1.0). Breaking changes are
allowed freely — there is no need for backward compatibility, deprecation shims,
or migration paths.

## Stack

- **Backend:** Python 3.12+ / FastAPI / SQLAlchemy 2.0 async / Alembic
- **Frontend:** React 19 + TypeScript (strict) + Vite
- **Database:** SQLite with aiosqlite (WAL mode for concurrency)
- **LLM Access:** LiteLLM (standard providers) + httpx (custom/RAG endpoints)
- **State Management:** Zustand (one store per domain)
- **Styling:** Tailwind CSS + shadcn/ui components
- **Testing:** pytest + pytest-asyncio (backend), Vitest + React Testing Library (frontend)
- **Linting:** ruff (backend), ESLint + Prettier (frontend)
- **Package Managers:** uv (backend, never pip), npm (frontend)
- **Container:** Podman/Docker with Compose v2

## Commands

```bash
# Development
make dev                          # Start backend (port 8000) + frontend (port 5173)
make check-deps                   # Validate uv, node, npm, docker/podman installed

# Backend (always prefix with uv run)
cd backend && uv run pytest -v                   # all tests
cd backend && uv run pytest -v tests/unit/       # unit tests only
cd backend && uv run pytest -k "test_name"       # specific test
cd backend && uv run ruff check .                # lint
cd backend && uv run ruff format .               # format

# Frontend
cd frontend && npm test -- --run                 # all tests
cd frontend && npm run lint                      # lint
cd frontend && npm run format                    # format
cd frontend && npm run dev                       # dev server

# Docker
docker compose up -d                             # dev environment
docker compose -f docker-compose.prod.yml up -d  # production

# Docs
make docs-serve                   # Serve MkDocs locally
make docs-build                   # Build static documentation site
```

## Architecture

```
Browser (React SPA)
  |  REST + WebSocket
  v
FastAPI backend (port 8000)
  |  SQLAlchemy async       YAML registries
  v                         v
SQLite (WAL mode)           config/*.yaml (providers, harnesses, tool servers, evaluators)
  |
  |  LiteLLM / httpx
  v
LLM providers (OpenAI, Anthropic, custom endpoints, local models)
```

### Backend packages (`backend/app/`)

- **api/v1/** — REST routers. One module per resource (evaluations, datasets,
  results, sessions, providers, harnesses, tool_servers, evaluators, judges,
  rubrics, artifacts, api_keys, health, dataset_import).
- **adapters/** — Evaluation scoring adapters. `EvaluationAdapter` ABC in
  `base.py`, `LiteLLMJudgeAdapter` implementation, factory + evaluator registry.
- **agent_backends/** — Agent LLM backends for interactive chat (LiteLLM
  streaming, custom httpx).
- **rag_backends/** — RAG retrieval+generation backends (HTTP, PgVector).
- **harnesses/** — Agent harness subsystem. `SubprocessHarness` spawns CLI tools;
  output parsers (goose, default) extract structured results.
- **mcp/** — MCP (Model Context Protocol) tool server lifecycle management.
- **services/** — Business logic. `eval_runner.py` is the consolidated evaluation
  orchestrator with `ModeRunner` implementations (QA, Arena, RAG).
  `agent_chat_service.py` handles multi-turn conversations with tool execution.
- **models/** — SQLAlchemy ORM models (evaluation, dataset, result, session,
  artifact, rubric, judge_config, api_key).
- **schemas/** — Pydantic request/response schemas. `PaginatedResponse` for
  DB-backed collections; RFC 7807 `ProblemDetail` for errors.
- **websocket/** — `/ws/session/{session_id}` (agent chat),
  `/ws/progress/{evaluation_id}` (evaluation progress with replay buffer).
- **core/** — Config (`Settings` via Pydantic), database engine + `TZDateTime`
  TypeDecorator, `YAMLBackedRegistry` base class, exceptions, security, rate
  limiter.

### Frontend layout (`frontend/src/`)

- **pages/** — Route-level components (Dashboard, QAEvaluation, RAGEvaluation,
  ArenaComparison, AgentEvaluation, Datasets, Results, Sessions, Settings, etc.).
- **components/** — Domain-grouped UI (chat, datasets, evaluation, results,
  settings, notifications, layout, ui primitives).
- **stores/** — Zustand stores, one per domain. Each store manages its own API
  calls and error state.
- **services/** — `api.ts` — typed HTTP client wrapping `fetch`.
- **types/** — TypeScript type definitions matching backend schemas.

### Supporting directories

- **config/** — YAML registry files (providers, harnesses, tool_servers,
  evaluators). Hot-reloaded by `YAMLBackedRegistry`.
- **environments/** — Docker Compose templates, TMT plans, Ansible playbooks,
  RAG demo setup.
- **docs/** — MkDocs Material documentation site.
- **examples/datasets/** — Sample Q&A datasets (YAML + JSONL).

## Database

- **Engine**: SQLite via SQLAlchemy 2.0 async with aiosqlite driver.
- **Migrations**: Alembic, auto-run at startup. For custom `DATABASE_URL`, run
  manually: `cd backend && uv run alembic upgrade head`.
- **WAL mode**: enabled for concurrent read access during evaluations.
- **Connection string**: `sqlite+aiosqlite:///./eval_studio.db` (configurable
  via `DATABASE_URL` env var).
- **TZDateTime**: custom TypeDecorator that re-attaches UTC on read (SQLite
  strips timezone info). All DateTime columns use it.
- **FK constraints**: all reference columns have explicit `ondelete` directives
  (RESTRICT, CASCADE, or SET NULL). `PRAGMA foreign_keys=ON` in production and
  tests.

## API Patterns

- All REST endpoints live under `/api/v1/`.
- Request/response schemas are Pydantic models in `backend/app/schemas/`.
- Error responses follow RFC 7807 Problem Details. 422 validation errors include
  a structured `errors` field with per-field details.
- DB-backed collections return `PaginatedResponse` (`items`, `total`, `page`,
  `page_size`, `pages`). Config/registry endpoints return bare arrays.
- WebSocket endpoints: `/ws/session/{session_id}`, `/ws/progress/{evaluation_id}`.

## Python Best Practices (backend/)

### Code Organization
- Import statements at the top, after module docstrings.
- Group imports: stdlib, third-party, project-internal. Separated by blank lines.
  Ruff handles sorting automatically.
- One module per file. Keep files focused on a single responsibility.

### Type Safety
- Add type hints to all function signatures (parameters and return types).
- Use `str | None` union syntax (not `Optional[str]`).
- Use Pydantic models for all external data validation (API inputs, config
  parsing). Use plain dataclasses for internal data transfer.
- Validate at system boundaries, trust internal code.

### Async
- All database and HTTP operations must be async (`async def`, `await`).
- Blocking file I/O must be wrapped in `asyncio.to_thread()`.
- Never use synchronous SQLAlchemy sessions or `requests` library.

### Error Handling
- Use specific exception types — never bare `except:`.
- Include context in error messages (what failed, which ID, what was expected).
- Use `AppException`/`ValidationException` from `core/exceptions.py` for API
  errors — they produce RFC 7807 responses automatically.
- Use `sanitize_error_for_client()` before surfacing internal errors to users.

### Testing
- Framework: pytest + pytest-asyncio. `@pytest.mark.asyncio` on all async tests.
- Tests live in `backend/tests/unit/` and `backend/tests/integration/`.
- File naming: `test_<module>.py`.
- Use factory functions to build test data, not raw dicts.
- Test public behavior, not implementation details.
- **YAML config isolation**: tests must NEVER use real config file paths. Use
  `tmp_path` fixtures or `registry.isolated()` to create isolated temp configs.
  Using real paths erases contributor configurations.

### Naming
- Files: `snake_case.py`
- Classes: `PascalCase`
- Functions/variables: `snake_case`
- Constants: `UPPER_SNAKE_CASE`
- Private helpers: `_leading_underscore`

### SQLAlchemy / Alembic
- Always use `TZDateTime` (not `DateTime`) for timestamp columns.
- Relationships should use `lazy="raise"` + `passive_deletes=True` — never
  `lazy="selectin"` (causes N+1 queries on every evaluation load).
- Add explicit `ondelete` to all ForeignKey declarations.
- New migrations: `cd backend && uv run alembic revision --autogenerate -m "description"`.
  Verify the generated migration before committing.

### FastAPI
- Router per resource in `api/v1/`.
- Use dependency injection for database sessions (`Depends(get_db)`).
- Return Pydantic response models explicitly (not raw dicts).
- Use `PaginatedResponse` for list endpoints backed by the database.

### Logging
- Use `structlog` via the project's configured logger — never raw `print()` or
  `logging.getLogger()`.
- Log at appropriate levels: debug for internals, info for lifecycle events,
  warning for recoverable issues, error for failures.

## TypeScript Best Practices (frontend/)

### Code Organization
- Imports at the top: React, third-party, project-internal. Separated by blank
  lines.
- One component per file. Colocate tests: `Foo.tsx` + `Foo.test.tsx`.
- Prefer named exports over default exports.

### Type Safety
- **Never use `any`**. Use `unknown` and narrow with type guards.
- Add explicit return types to exported functions and components.
- Use `interface` for object shapes, `type` for unions/intersections/aliases.
- Validate external data at system boundaries (API responses) with runtime
  checks or Zod schemas.

### React
- Functional components with hooks only — no class components.
- Memoize expensive computations with `useMemo` / `useCallback`.
- Extract shared stateful logic into custom hooks (`hooks/`).
- State belongs in Zustand stores, not component state, unless it's purely
  local UI state (form inputs, toggles).

### Error Handling
- Never use bare `catch {}` or `.catch(() => {})`. Always handle or log.
- API errors should surface to the user via the notification store.
- Include context in error messages (what failed, which resource).

### API Client
- All API calls go through `services/api.ts` using the typed `request<T>()`
  helper.
- Never use raw `fetch()` directly in components or stores.

### Testing
- Framework: Vitest + React Testing Library.
- Test files colocated with source: `Component.test.tsx`, `module.test.ts`.
- Test user-visible behavior, not implementation details.
- Use `vi.fn()` for mocks, `vi.spyOn()` for spies.
- Clean up side effects in `afterEach()`.

### Naming
- Files: `PascalCase.tsx` for components, `camelCase.ts` for modules
- Components/Types: `PascalCase`
- Functions/Variables: `camelCase`
- Constants: `UPPER_SNAKE_CASE`
- Test descriptions: plain English, describe behavior not implementation

### Styling
- Tailwind CSS utility classes. Avoid custom CSS unless truly necessary.
- Use shadcn/ui components from `components/ui/` as the base layer.
- Keep component-specific styling in the component file (className props).

## Commit Messages

Conventional Commits format:

```
<type>(<scope>): <description>

[optional body]
```

**Types**: `feat`, `fix`, `refactor`, `test`, `docs`, `chore`, `ci`
**Scopes**: `backend`, `frontend`, `infra`, `docs`, `env`

## Common Pitfalls

1. **SELinux `:z` volume labels**: On Fedora/RHEL hosts, Docker volume mounts
   MUST include `:z` suffix (e.g., `./backend:/app:z`). Without it, containers
   cannot read host directories when SELinux is enforcing.

2. **`docker compose` vs `docker-compose`**: Use `docker compose` (v2 plugin
   syntax), NOT `docker-compose` (standalone v1 binary).

3. **uv, not pip**: Never use `pip install`. Always `uv sync` for deps, `uv run`
   for execution. The `uv.lock` file must be committed.

4. **`uv run` prefix**: Every Python command (pytest, ruff, alembic, uvicorn)
   must use `uv run`. Running `pytest` directly uses the system Python.

5. **Frontend node_modules in Docker**: The named volume prevents host/container
   sharing. Run `npm install` independently on both.

6. **Environment variable precedence**: `docker-compose.yml` `environment:`
   values override `.env` file values.

7. **Test isolation for YAML configs**: Tests must NEVER use actual config file
   paths. Always use `tmp_path` or `registry.isolated()`. Using real paths
   erases contributor configurations during development.
