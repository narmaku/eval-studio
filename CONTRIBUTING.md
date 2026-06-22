# Contributing to eval-studio

Thank you for your interest in contributing to eval-studio! This guide covers
everything you need to get started.

## Prerequisites

Ensure the following tools are installed before starting:

| Tool            | Minimum Version | Check Command         | Install Guide                                       |
|-----------------|----------------|-----------------------|-----------------------------------------------------|
| Python          | 3.11+          | `python3 --version`   | https://www.python.org/downloads/                   |
| Node.js         | 22+            | `node --version`      | https://nodejs.org/                                 |
| uv              | latest         | `uv --version`        | https://docs.astral.sh/uv/getting-started/installation/ |
| Docker or Podman| latest         | `docker --version`    | https://docs.docker.com/get-docker/                 |
| GNU Make        | 3.80+          | `make --version`      | Usually pre-installed on Linux/macOS                |

You can verify all dependencies at once with:

```bash
make check-deps
```

## Getting Started

1. **Clone the repository:**
   ```bash
   git clone https://github.com/narmaku/eval-studio.git
   cd eval-studio
   ```

2. **Copy the environment file:**
   ```bash
   cp .env.example .env
   ```
   Edit `.env` to add your LLM API key (required for judge features).

3. **Start development servers:**
   ```bash
   make dev
   ```
   This starts:
   - Backend at http://localhost:8000 (FastAPI with auto-reload)
   - Frontend at http://localhost:5173 (Vite dev server)

4. **Alternatively, use Docker Compose:**
   ```bash
   docker compose up -d
   ```

## Project Structure

| Directory        | Description                                          |
|------------------|------------------------------------------------------|
| `backend/`       | FastAPI Python application (API, adapters, judges)   |
| `frontend/`      | React TypeScript application (UI, state management)  |
| `environments/`  | Docker Compose templates, TMT plans, Ansible playbooks, scenario definitions |
| `docs/`          | MkDocs Material documentation site                   |
| `examples/`      | Sample datasets, judge configurations                |

## Database Migrations

Schema migrations run automatically on startup. The migration chain was
squashed to a single initial revision (pre-1.0, no external deployments).

If you have an existing local database from before the squash, delete it
and let the app recreate it:

```bash
rm -f backend/data/eval_studio.db*
make dev   # auto-migration creates a fresh DB
```

Alternatively, stamp the existing database without replaying migrations:

```bash
cd backend && uv run alembic stamp head
```

**Policy:** migration squashes are acceptable before the first tagged
release. After that, every schema change must be a forward-compatible
Alembic revision.

## Development Workflow

1. **Create a branch** from `main`:
   ```bash
   git checkout -b feat/my-feature
   ```

2. **Make your changes** following the coding conventions below.

3. **Run linters and tests:**
   ```bash
   make lint
   make test
   ```

4. **Commit** using Conventional Commits format (see below).

5. **Push and open a pull request** against `main`.

## Commit Message Format

We use [Conventional Commits](https://www.conventionalcommits.org/):

```
<type>(<scope>): <description>

[optional body]
```

### Types

| Type       | When to use                              |
|------------|------------------------------------------|
| `feat`     | A new feature                            |
| `fix`      | A bug fix                                |
| `refactor` | Code change that neither fixes nor adds  |
| `test`     | Adding or updating tests                 |
| `docs`     | Documentation changes                    |
| `chore`    | Maintenance tasks (deps, config, etc.)   |
| `ci`       | CI/CD changes                            |

### Scopes

| Scope      | Area                                     |
|------------|------------------------------------------|
| `backend`  | Backend Python code                      |
| `frontend` | Frontend TypeScript code                 |
| `infra`    | Makefile, Docker, CI/CD                  |
| `docs`     | Documentation                            |
| `env`      | Environment templates and scenarios      |

### Examples

```
feat(backend): add Q&A evaluation adapter
fix(frontend): prevent race condition in WebSocket reconnect
docs(infra): update CONTRIBUTING.md with adapter guide
test(backend): add integration tests for RAG adapter
```

## Pull Request Process

1. Create a PR against `main` with a clear title following commit format.
2. Fill in the PR template:
   - **Summary**: 1-3 bullet points describing the changes
   - **Test plan**: checklist of testing steps
3. Ensure CI passes (lint, backend tests, frontend tests).
4. Request review from a maintainer.
5. PRs are merged via **squash merge** for a clean history.

## Testing Expectations

### Backend

- Tests live in `backend/tests/unit/` and `backend/tests/integration/`
- File naming: `test_<module>.py`
- Use pytest fixtures from `conftest.py` for test database, async client, etc.
- All new features must include unit tests; integration tests recommended.
- Run: `make test-backend` or `cd backend && uv run pytest -v`

### Frontend

- Tests are colocated with source files: `<Component>.test.tsx`
- Use React Testing Library for component tests.
- All new components must include tests.
- Run: `make test-frontend` or `cd frontend && npm test -- --run`

## Code Style

### Python

- Formatter/linter: **ruff** (configured in `backend/pyproject.toml`)
- Line length: 120 characters
- Type hints required on all public functions
- Docstrings: Google style, for public API methods only
- Use `uv run` for all Python commands (never bare `python` or `pip`)

### TypeScript

- Linter: **ESLint** (configured in `frontend/`)
- Formatter: **Prettier** (configured in `frontend/.prettierrc`)
- Strict mode enabled; `any` type is not allowed
- Use functional components with hooks

## How to Add a New Evaluation Adapter

Evaluation adapters implement the `EvaluationAdapter` abstract base class.

1. **Create the adapter file:**
   ```bash
   touch backend/app/adapters/my_adapter.py
   ```

2. **Implement the interface:**
   ```python
   from app.adapters.base import EvaluationAdapter

   class MyAdapter(EvaluationAdapter):
       async def setup(self, config: dict) -> None:
           """Initialize the adapter with configuration."""
           ...

       async def evaluate(self, inputs: list) -> list:
           """Run evaluation on the given inputs."""
           ...

       async def teardown(self) -> None:
           """Clean up resources."""
           ...

       async def get_results(self) -> dict:
           """Return evaluation results."""
           ...
   ```

3. **Register** the adapter in the adapter registry.

4. **Write tests** in `backend/tests/unit/test_my_adapter.py`.

## How to Add a New Environment Provider

Environment providers implement the `EnvironmentProvider` abstract base class.

1. **Create the provider file:**
   ```bash
   touch backend/app/environments/my_provider.py
   ```

2. **Implement the interface:**
   ```python
   from app.environments.base import EnvironmentProvider

   class MyProvider(EnvironmentProvider):
       async def provision(self, config: dict) -> dict:
           """Provision the environment and return connection details."""
           ...

       async def connect(self, connection_info: dict) -> None:
           """Establish connection to the provisioned environment."""
           ...

       async def execute(self, command: str) -> str:
           """Execute a command in the environment."""
           ...

       async def teardown(self) -> None:
           """Tear down the provisioned environment."""
           ...
   ```

3. **Register** the provider and write tests.

## How to Add a New Evaluation Scenario

1. **Create a scenario YAML** in `environments/scenarios/`:
   ```yaml
   name: my-scenario
   description: Description of what this scenario tests.
   category: networking  # or security, storage, etc.
   difficulty: beginner  # beginner, intermediate, advanced

   environment:
     type: compose
     template: rhel9-base

   setup:
     steps:
       - command: "systemctl stop my-service"
         description: "Break the service"

   success_criteria:
     - description: "Service is running"
       check: "systemctl is-active my-service"
       expected: "active"

   max_turns: 10
   timeout_seconds: 300
   tags: [my-tag]
   ```

2. **Optionally**, add a Docker Compose template in `environments/compose/<name>/`
   with a `docker-compose.yml` and `Dockerfile`.

## Questions?

If you have questions about contributing, please open an issue on GitHub
or reach out to the maintainers.
