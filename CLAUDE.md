# CLAUDE.md -- eval-studio

## Project Overview

eval-studio is a workspace for building, running, and improving AI evaluations.
It goes beyond evaluation execution — it covers everything needed to be successful
in building AI evaluations of any kind and iterating on changes in internal AI
tooling and AI products.

It is a workspace for engineers (and non-technical subject-matter experts) to build
datasets, scoring metrics/rubrics, and telemetry integrations, then use them
seamlessly with any evaluation system onboarded into the platform. The first
integration target is lightspeed-evaluation.

Evaluation modes: Q&A benchmarks, RAG evaluation, interactive agent sessions, and
side-by-side model arena. The pluggable adapter architecture supports onboarding
external evaluation frameworks as scoring backends.

## Architecture Summary

### Adapter Pattern

All evaluation backends implement the `EvaluationAdapter` ABC defined in
`backend/app/adapters/base.py`. Each adapter handles a specific evaluation
mode (Q&A, RAG, agent, comparison). To add a new adapter, create a class
that implements the interface and register it in the adapter registry.

Environment provisioning follows the same pattern via `EnvironmentProvider` ABC
in `backend/app/environments/base.py`. Providers include Docker Compose
(local containers), BYOE (bring your own environment via SSH), and TMT
(Testing Farm API for real RHEL machines).

### LLM Access

All LLM calls go through **LiteLLM** -- never import provider SDKs directly.
This allows switching between OpenAI, Anthropic, local models, etc. by changing
the `LITELLM_MODEL` and `LITELLM_API_KEY` environment variables.

### Real-Time Communication

WebSocket connections (via FastAPI WebSocket endpoints) power real-time features:
interactive chat sessions with agents, evaluation progress streaming, and
collaborative features. Frontend connects via native WebSocket API.

## Directory Structure

```
eval-studio/
├── backend/                      # FastAPI Python application
│   ├── app/
│   │   ├── main.py               # FastAPI app factory, middleware, lifespan
│   │   ├── api/
│   │   │   └── v1/               # Versioned REST endpoints
│   │   │       ├── evaluations.py
│   │   │       ├── datasets.py
│   │   │       ├── environments.py
│   │   │       ├── results.py
│   │   │       └── health.py
│   │   ├── adapters/             # Evaluation backend adapters
│   │   │   ├── base.py           # EvaluationAdapter ABC
│   │   │   ├── qa.py             # Q&A benchmark adapter
│   │   │   ├── rag.py            # RAG evaluation adapter
│   │   │   ├── agent.py          # Interactive agent adapter
│   │   │   └── comparison.py     # Side-by-side comparison adapter
│   │   ├── environments/         # Environment provisioning
│   │   │   ├── base.py           # EnvironmentProvider ABC
│   │   │   ├── compose.py        # Docker Compose provider
│   │   │   ├── byoe.py           # Bring Your Own Environment (SSH)
│   │   │   └── tmt.py            # Testing Farm provider
│   │   ├── judges/               # LLM-as-judge scoring
│   │   │   ├── base.py           # Judge ABC
│   │   │   ├── single.py         # Single model judge
│   │   │   └── panel.py          # Multi-model panel judge
│   │   ├── models/               # SQLAlchemy ORM models
│   │   ├── schemas/              # Pydantic request/response schemas
│   │   ├── services/             # Business logic layer
│   │   └── core/                 # Config, database, middleware
│   │       ├── config.py         # Settings (from env vars via Pydantic)
│   │       ├── database.py       # Async SQLAlchemy engine + session
│   │       └── exceptions.py     # RFC 7807 error handling
│   ├── tests/
│   │   ├── unit/
│   │   └── integration/
│   ├── alembic/                  # Database migrations
│   ├── pyproject.toml
│   └── uv.lock
├── frontend/                     # React TypeScript application
│   ├── src/
│   │   ├── components/           # Shared UI components
│   │   ├── pages/                # Route-level page components
│   │   ├── stores/               # Zustand state stores (one per domain)
│   │   ├── hooks/                # Custom React hooks
│   │   ├── lib/                  # Utilities, API client, types
│   │   └── App.tsx
│   ├── package.json
│   └── vite.config.ts
├── environments/                 # Environment definitions
│   ├── compose/                  # Docker Compose templates per scenario
│   │   ├── rhel9-base/           # Base RHEL 9 (UBI) container
│   │   └── ssh-broken/           # SSH failure scenario
│   ├── scenarios/                # Scenario definition YAML files
│   ├── tmt/                      # TMT/Testing Farm plans
│   └── ansible/                  # Ansible playbooks for BYOE setup
├── docs/                         # MkDocs Material documentation
│   ├── mkdocs.yml
│   └── docs/
│       ├── index.md
│       ├── getting-started.md
│       ├── evaluation-modes.md
│       ├── adapters.md
│       ├── environments.md
│       └── api-reference.md
├── examples/                     # Sample configurations
│   ├── datasets/                 # Sample Q&A datasets (YAML + JSONL)
│   └── judges/                   # Judge configuration templates
├── .github/workflows/            # CI/CD pipelines
│   ├── ci.yml                    # Lint + test + container smoke
│   └── release.yml               # Build + push to ghcr.io on tag
├── Makefile                      # Build system entry point
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
- **Migrations**: Alembic (run with `cd backend && uv run alembic upgrade head`)
- **WAL mode**: enabled for concurrent read access during evaluations
- **Connection string**: `sqlite+aiosqlite:///./data/eval_studio.db` (configurable
  via `DATABASE_URL` environment variable)
- **Session management**: async context manager in `backend/app/core/database.py`

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
- Health check endpoint: `GET /api/v1/health`
- WebSocket endpoints: `/ws/chat/{session_id}`, `/ws/progress/{run_id}`

## State Management (Frontend)

- **Zustand** stores, one per domain: evaluations, datasets, results,
  environments, settings
- Each store is a standalone module in `frontend/src/stores/`
- Stores handle their own API calls and error states
- WebSocket state managed in a dedicated connection store
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

1. Create `backend/app/adapters/<name>.py`
2. Implement the `EvaluationAdapter` ABC (methods: `setup()`, `evaluate()`,
   `teardown()`, `get_results()`)
3. Register the adapter in the adapter registry
4. Add Pydantic schemas for any adapter-specific config
5. Write tests in `backend/tests/unit/test_<name>_adapter.py`
6. Update the API endpoint to accept the new adapter type

### Adding a New Environment Provider

1. Create `backend/app/environments/<name>.py`
2. Implement the `EnvironmentProvider` ABC (methods: `provision()`,
   `connect()`, `execute()`, `teardown()`)
3. Register the provider in the environment registry
4. Add configuration schema
5. Write tests
6. If applicable, add a Docker Compose template in `environments/compose/<name>/`

### Adding a New API Endpoint

1. Create or extend a router in `backend/app/api/v1/`
2. Define Pydantic request/response schemas in `backend/app/schemas/`
3. Implement business logic in `backend/app/services/`
4. Add the router to the FastAPI app in `backend/app/main.py`
5. Write integration tests that exercise the endpoint

### Adding a New Frontend Page

1. Create page component in `frontend/src/pages/<PageName>/`
2. Add route in the router configuration
3. Create or extend relevant Zustand store in `frontend/src/stores/`
4. Add API client methods in `frontend/src/lib/api/`
5. Write component tests with React Testing Library
