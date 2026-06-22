# CLAUDE.md -- eval-studio

## Project Overview

eval-studio is a workspace for building, running, and improving AI evaluations.
It covers dataset creation, scoring metrics/rubrics, and telemetry integrations,
used seamlessly with evaluation systems onboarded into the platform. The first
integration target is lightspeed-evaluation.

Evaluation modes: Q&A benchmarks, RAG evaluation, interactive agent sessions, and
side-by-side model arena. Evaluator adapters are pluggable — the evaluator
registry (`config/evaluators.yaml`) maps named evaluators to adapter classes, and
evaluations reference an evaluator by ID.

## Architecture Summary

### Evaluation Flow

All evaluation modes share a single orchestrator: `backend/app/services/eval_runner.py`.
Mode-specific logic is encapsulated in `ModeRunner` implementations (QARunner,
ArenaRunner, RAGRunner) within the same file. The orchestrator handles lifecycle
management (status transitions, failure handling, artifact generation) while runners
handle mode-specific preparation, task generation, and per-item execution.

### LLM Access

LLM calls go through **LiteLLM** for standard providers (configured via the
provider registry in `config/providers.yaml`). Custom providers use a direct
**httpx** adapter (`backend/app/agent_backends/custom_httpx_agent.py`) for
endpoints that don't follow the OpenAI API format. RAG backends also use httpx
directly for retrieval endpoints.

Provider configuration is managed via YAML-backed registries, not environment
variables. Each provider entry specifies its model, API key env var, proxy
settings, and SSL configuration.

### Agent Chat

Interactive agent sessions use a harness-based architecture. Harnesses
(`config/harnesses.yaml`) define CLI tools that agents interact through.
The `SubprocessHarness` spawns harness processes, and MCP (Model Context Protocol)
servers provide tool capabilities. The agent chat service
(`backend/app/services/agent_chat_service.py`) orchestrates multi-turn
conversations with tool execution.

### YAML-Backed Registries

Four subsystems use YAML config files instead of the database:
- `config/providers.yaml` — LLM provider profiles
- `config/harnesses.yaml` — harness definitions for agent chat
- `config/tool_servers.yaml` — MCP tool server definitions
- `config/evaluators.yaml` — evaluator adapter registrations

All extend `YAMLBackedRegistry` (`backend/app/core/registry_base.py`) which
provides hot-reload, persistence, and test isolation via `isolated()`.

### Real-Time Communication

WebSocket endpoints power real-time features:
- `/ws/session/{session_id}` — interactive agent chat sessions
- `/ws/progress/{evaluation_id}` — evaluation progress streaming with replay buffer

Frontend connects via native WebSocket API.

## Directory Structure

```
eval-studio/
├── backend/                      # FastAPI Python application
│   ├── app/
│   │   ├── main.py               # FastAPI app factory, lifespan (auto-migration)
│   │   ├── api/v1/               # REST routers (16 modules)
│   │   │   ├── evaluations.py    # CRUD + run/rerun
│   │   │   ├── datasets.py       # Dataset CRUD
│   │   │   ├── dataset_import.py # File upload + smart import
│   │   │   ├── results.py        # Evaluation results
│   │   │   ├── sessions.py       # Agent chat sessions + scoring
│   │   │   ├── providers.py      # Provider registry CRUD
│   │   │   ├── harnesses.py      # Harness registry CRUD
│   │   │   ├── tool_servers.py   # Tool server registry CRUD
│   │   │   ├── evaluators.py     # Evaluator registry CRUD
│   │   │   ├── judges.py         # Judge config CRUD
│   │   │   ├── rubrics.py        # Rubric CRUD + LLM generation
│   │   │   ├── artifacts.py      # Evaluation artifacts
│   │   │   ├── api_keys.py       # API key management
│   │   │   ├── health.py         # Health check
│   │   │   └── _registry_helpers.py  # Shared YAML write + validation
│   │   ├── adapters/             # Evaluation scoring adapters
│   │   │   ├── base.py           # EvaluationAdapter ABC + Score dataclass
│   │   │   ├── litellm_judge.py  # LiteLLM-based judge (QA, RAG, conversation)
│   │   │   ├── factory.py        # Adapter creation from evaluator config
│   │   │   └── registry.py       # Evaluator registry (YAML-backed)
│   │   ├── agent_backends/       # Agent LLM backends for chat
│   │   │   ├── litellm_agent.py  # LiteLLM streaming agent
│   │   │   └── custom_httpx_agent.py  # Direct httpx agent
│   │   ├── rag_backends/         # RAG retrieval+generation backends
│   │   │   ├── http_adapter.py   # HTTP-based RAG endpoint
│   │   │   └── pgvector_adapter.py  # PgVector similarity search
│   │   ├── harnesses/            # Agent harness subsystem
│   │   │   ├── subprocess_harness.py  # Subprocess-based harness
│   │   │   ├── registry.py       # Harness registry (YAML-backed)
│   │   │   └── parsers/          # Output format parsers (goose, default)
│   │   ├── mcp/                  # MCP tool server management
│   │   │   ├── manager.py        # Server lifecycle manager
│   │   │   └── client.py         # MCP protocol client
│   │   ├── models/               # SQLAlchemy ORM models
│   │   ├── schemas/              # Pydantic request/response schemas
│   │   ├── services/             # Business logic layer
│   │   │   ├── eval_runner.py    # Consolidated evaluation orchestrator
│   │   │   ├── agent_chat_service.py  # Agent chat with tool execution
│   │   │   ├── dataset_service.py     # Dataset persistence helpers
│   │   │   ├── dataset_import_service.py  # File parsing + schema extraction
│   │   │   ├── rubric_service.py      # Rubric LLM generation/refinement
│   │   │   ├── provider_utils.py      # Model config resolution
│   │   │   ├── run_service.py         # Run-and-wait orchestration
│   │   │   └── artifact_generation.py # Post-eval artifact creation
│   │   ├── websocket/            # WebSocket endpoints
│   │   │   ├── chat.py           # /ws/session/{session_id}
│   │   │   └── progress.py       # /ws/progress/{evaluation_id}
│   │   └── core/                 # Config, database, middleware
│   │       ├── config.py         # Settings (Pydantic, from env vars)
│   │       ├── database.py       # Async SQLAlchemy engine + TZDateTime
│   │       ├── exceptions.py     # RFC 7807 error handling
│   │       ├── security.py       # API key auth middleware
│   │       ├── providers.py      # Provider registry (YAML-backed)
│   │       ├── tool_servers.py   # Tool server registry (YAML-backed)
│   │       ├── registry_base.py  # YAMLBackedRegistry base class
│   │       └── rate_limiter.py   # Token-bucket rate limiter
│   ├── tests/
│   │   ├── unit/
│   │   └── integration/
│   ├── alembic/                  # Database migrations (single squashed revision)
│   ├── pyproject.toml
│   └── uv.lock
├── frontend/                     # React TypeScript application
│   ├── src/
│   │   ├── components/           # Shared UI components
│   │   │   ├── chat/             # Agent chat interface
│   │   │   ├── datasets/         # Dataset management UI
│   │   │   ├── evaluation/       # Evaluation config + progress
│   │   │   ├── results/          # Result display + artifacts
│   │   │   ├── settings/         # Provider/harness/tool config
│   │   │   ├── notifications/    # Toast notification system
│   │   │   ├── layout/           # App shell, sidebar, nav
│   │   │   └── ui/               # Generic UI primitives
│   │   ├── pages/                # Route-level page components
│   │   ├── stores/               # Zustand state stores (one per domain)
│   │   ├── services/             # API client (api.ts)
│   │   ├── types/                # TypeScript type definitions
│   │   └── App.tsx
│   ├── package.json
│   └── vite.config.ts
├── config/                       # YAML registry config files
│   ├── providers.yaml
│   ├── harnesses.yaml
│   ├── tool_servers.yaml
│   └── evaluators.yaml
├── environments/                 # Environment definitions
│   ├── compose/                  # Docker Compose templates
│   ├── rag-demo/                 # RAG demo environment
│   ├── scenarios/                # Scenario definition YAML files
│   ├── tmt/                      # TMT/Testing Farm plans
│   └── ansible/                  # Ansible playbooks
├── docs/                         # MkDocs Material documentation
├── examples/
│   └── datasets/                 # Sample Q&A datasets (YAML + JSONL)
├── .github/workflows/            # CI/CD pipelines
├── Makefile                      # Build system entry point
├── dev.sh                        # Development launcher (used by make dev)
├── docker-compose.yml            # Development environment
├── docker-compose.prod.yml       # Production deployment
├── Containerfile                 # Multi-stage production build
├── nginx.conf                    # Production reverse proxy config
├── .env.example                  # Environment variable template
├── CLAUDE.md                     # This file
├── CONTRIBUTING.md               # Contributor guide
├── LICENSE                       # Apache 2.0
└── README.md                     # Project overview
```

## Build, Test, and Lint Commands

All commands are available as Makefile targets. Run `make help` to see them all.

| Command              | What it does                                         |
|----------------------|------------------------------------------------------|
| `make help`          | Print all available targets with descriptions        |
| `make check-deps`    | Validate uv, node, npm, docker/podman are installed  |
| `make dev`           | Start backend (port 8000) + frontend (port 5173)     |
| `make test`          | Run all tests (backend + frontend)                   |
| `make test-backend`  | Run `cd backend && uv run pytest -v`                 |
| `make test-frontend` | Run `cd frontend && npm test -- --run`               |
| `make lint`          | Run ruff check/format on backend, eslint on frontend |
| `make format`        | Run ruff format + fix on backend, prettier on frontend|
| `make build`         | Production build (uv sync --no-dev + npm run build)  |
| `make clean`         | Remove build artifacts, caches, and site/ directory  |
| `make docker-build`  | Build production container from Containerfile        |
| `make docker-up`     | Start dev environment via docker compose             |
| `make docker-down`   | Stop dev environment via docker compose              |
| `make docs-serve`    | Serve MkDocs documentation locally                   |
| `make docs-build`    | Build static documentation site                      |

### Running individual commands directly

```bash
# Backend (always prefix with uv run)
cd backend && uv run pytest -v                      # all tests
cd backend && uv run pytest -v tests/unit/           # unit tests only
cd backend && uv run pytest -k "test_qa_adapter"     # specific test
cd backend && uv run ruff check .                    # lint
cd backend && uv run ruff format .                   # format

# Frontend
cd frontend && npm test -- --run                     # all tests
cd frontend && npm run lint                          # lint
cd frontend && npm run format                        # format
cd frontend && npm run dev                           # dev server

# Docker
docker compose up -d                                 # dev environment
docker compose --profile litellm up -d               # dev + LiteLLM proxy
docker compose -f docker-compose.prod.yml up -d      # production
```

## Coding Conventions

### Python (backend/)

- **Package manager**: uv (never pip). Always use `uv run` to execute commands.
- **Linter/formatter**: ruff (configured in `backend/pyproject.toml`)
- **Line length**: 120 characters
- **Naming**: snake_case for functions/variables, PascalCase for classes
- **Type hints**: required on all public function signatures
- **Docstrings**: Google style, required for public API methods only
- **Import sorting**: handled by ruff (isort-compatible)
- **Async**: all database and HTTP operations must be async
- **Testing**: pytest + pytest-asyncio. Tests in `backend/tests/unit/` and
  `backend/tests/integration/`. File naming: `test_<module>.py`.

### TypeScript (frontend/)

- **Linter**: ESLint with TypeScript rules
- **Formatter**: Prettier (configured in `.prettierrc`)
- **Strict mode**: enabled in `tsconfig.json`
- **No `any`**: use `unknown` or explicit types instead
- **Naming**: camelCase for functions/variables, PascalCase for components/types
- **Components**: functional components with hooks, no class components
- **Testing**: Vitest + React Testing Library. Tests colocated with source:
  `<Component>.test.tsx` or `<module>.test.ts`.

### Commit Messages

Conventional Commits format:

```
<type>(<scope>): <description>

[optional body]
```

**Types**: `feat`, `fix`, `refactor`, `test`, `docs`, `chore`, `ci`
**Scopes**: `backend`, `frontend`, `infra`, `docs`, `env`

Examples:
- `feat(backend): add Q&A evaluation adapter`
- `fix(frontend): prevent race condition in WebSocket reconnect`
- `chore(infra): update CI to cache uv dependencies`

## Database

- **Engine**: SQLite via SQLAlchemy 2.0 async with aiosqlite driver
- **Migrations**: Alembic, auto-run at startup via `_run_alembic_migrations()` in
  the FastAPI lifespan. For custom `DATABASE_URL`, run manually:
  `cd backend && uv run alembic upgrade head`
- **WAL mode**: enabled for concurrent read access during evaluations
- **Connection string**: `sqlite+aiosqlite:///./eval_studio.db` (configurable
  via `DATABASE_URL` environment variable)
- **Session management**: async context manager in `backend/app/core/database.py`
- **TZDateTime**: custom TypeDecorator that re-attaches UTC on read (SQLite strips
  timezone info). All DateTime columns use `TZDateTime`.
- **FK constraints**: all reference columns have explicit `ondelete` directives
  (RESTRICT, CASCADE, or SET NULL). `PRAGMA foreign_keys=ON` enabled in production
  and tests.

## API Patterns

- All REST endpoints live under `/api/v1/`
- Request/response schemas defined as Pydantic models in `backend/app/schemas/`
- Error responses follow RFC 7807 Problem Details format:
  ```json
  {
    "type": "about:blank",
    "title": "Not Found",
    "status": 404,
    "detail": "Evaluation run abc-123 not found",
    "instance": "/api/v1/evaluations/abc-123"
  }
  ```
- 422 validation errors include structured `errors` field with per-field details
- DB-backed collections return paginated responses (`PaginatedResponse` with
  `items`, `total`, `page`, `page_size`, `pages`). Config/registry endpoints
  return bare arrays.
- Health check endpoint: `GET /api/v1/health`
- WebSocket endpoints: `/ws/session/{session_id}`, `/ws/progress/{evaluation_id}`

## State Management (Frontend)

- **Zustand** stores, one per domain: evaluations, datasets, results, providers,
  harnesses, evaluators, rubrics, sessions, notifications, toolServers, ui
- Each store is a standalone module in `frontend/src/stores/`
- Stores handle their own API calls and error states
- No Redux, no Context API for app state (only for theme/auth providers)

## Common Pitfalls

1. **SELinux `:z` volume labels**: On Fedora/RHEL hosts, Docker volume mounts
   MUST include `:z` suffix (e.g., `./backend:/app:z`). Without it, containers
   cannot read host directories when SELinux is enforcing. This is the #1
   cause of "works on Ubuntu, fails on Fedora" issues.

2. **`docker compose` vs `docker-compose`**: Use `docker compose` (v2 plugin
   syntax), NOT `docker-compose` (standalone v1 binary). The compose files use
   v2 specification (no `version:` key).

3. **uv, not pip**: Never use `pip install`. Always use `uv sync` to install
   dependencies and `uv run` to execute Python commands. The `uv.lock` file
   must be committed.

4. **SQLite WAL mode**: Must be explicitly enabled for concurrent reads during
   evaluation runs. Without WAL mode, concurrent writes will cause database
   locked errors.

5. **`uv run` prefix**: Every Python command (pytest, ruff, alembic, uvicorn)
   must be prefixed with `uv run` to use the correct virtual environment.
   Running `pytest` directly will likely use the system Python.

6. **Frontend node_modules in Docker**: The `frontend-node-modules` named
   volume prevents sharing node_modules between host and container. This avoids
   platform-specific native module conflicts. Run `npm install` on both host
   and container independently.

7. **Environment variable precedence**: `docker-compose.yml` `environment:`
   values override `.env` file values. If a variable appears in both, the
   `environment:` section wins.

8. **Test isolation for YAML configs**: Tests must NEVER use actual config
   file paths (e.g., `config/tool_servers.yaml`, `config/harnesses.yaml`).
   Always use `tmp_path` fixtures to create isolated temporary config files.
   Using real paths will erase contributor configurations during development.

## Development Workflows

### Adding a New Evaluation Adapter

1. Create a new adapter class in `backend/app/adapters/` implementing the
   `EvaluationAdapter` ABC (methods: `evaluate_qa()`, `evaluate_conversation()`,
   `evaluate_rag()`)
2. Register it in `config/evaluators.yaml` with a unique ID, name, and the
   fully-qualified adapter class path
3. The evaluator factory (`backend/app/adapters/factory.py`) will instantiate
   it via the registry entry's `adapter_class` field
4. Write tests in `backend/tests/unit/`

### Adding a New API Endpoint

1. Create or extend a router in `backend/app/api/v1/`
2. Define Pydantic request/response schemas in `backend/app/schemas/`
3. Implement business logic in `backend/app/services/`
4. Add the router to the FastAPI app in `backend/app/main.py`
5. Write integration tests that exercise the endpoint

### Adding a New Frontend Page

1. Create page component in `frontend/src/pages/`
2. Add route in the router configuration (`App.tsx`)
3. Create or extend relevant Zustand store in `frontend/src/stores/`
4. Add API client methods in `frontend/src/services/api.ts`
5. Write component tests with Vitest + React Testing Library
