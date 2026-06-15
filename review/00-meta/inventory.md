# Repository Inventory

Snapshot taken 2026-06-11 on branch `main` at commit `ffc4b27` ("fix(frontend): fix ArtifactsList not loading in React StrictMode"). 466 tracked files (excluding `node_modules/`, `.venv/`, caches).

## Top-level layout (actual, not as documented)

| Path | What it actually is | Status |
|------|--------------------|--------|
| `backend/` | FastAPI app (102 Python source files in `app/`, 74 test files) | Live |
| `frontend/` | React 19 + TS + Vite + Zustand + shadcn (≈180 files incl. tests) | Live |
| `clients/` | Hand-written Python SDK (sync + async) + Typer CLI, own `pyproject.toml`/`uv.lock` | **Not exercised by CI** |
| `config/` | `evaluators.yaml` (checked in) + `providers/harnesses/tool_servers.yaml.example` | Live; `providers.yaml.example` keys are stale |
| `environments/` | compose/rhel9-base, ssh-broken (README only), rag-demo Flask-ish demo app, scenarios/*.yaml, tmt/*.fmf, ansible/README | Mostly dead; backend environments API is 100% `501 Not Implemented` |
| `examples/` | sample datasets (used manually), `judges/*.yaml` (consumed by nothing) | Partially dead |
| `docs/` | MkDocs Material site, 7 pages | Mixed accuracy; adapters/environments pages are stubs describing unbuilt systems |
| Root infra | `Makefile`, `dev.sh`, `docker-compose.yml`, `docker-compose.prod.yml`, `Containerfile`, `backend/Dockerfile.dev`, `nginx.conf`, `.env.example` | Live, with drift (see INFRA issues) |
| `.github/workflows/` | `ci.yml` (lint, test-backend, test-frontend, container-smoke), `release.yml` (ghcr push on tag) | Live; `clients/` untested |

## Backend module map (`backend/app/`)

| Package | Files | Role | Notes |
|---------|-------|------|-------|
| `main.py` | 1 | App factory, CORS, correlation-id middleware, RFC7807 handlers, router includes, **2 ad-hoc raw-SQL data migrations in lifespan** | |
| `core/` | config, database, exceptions, logging, security, registry_base, providers, tool_servers, rate_limiter, subprocess_validation | settings, async engine + `Base`, auth, YAML registry base + 2 registries | Registries do sync file I/O; module-level singletons load at import |
| `models/` | 9 ORM models | api_key, artifact, dataset(+item), environment, evaluation(+judge_config), provider, result, rubric, session | `Provider` table is **dead** (no API writes, sole reader is an uncalled function) |
| `schemas/` | 16 Pydantic modules | request/response shapes | |
| `api/v1/` | 15 routers | REST endpoints | `environments.py` all-501; `evaluators.py` includes config-file upload mgmt |
| `services/` | 11 modules | evaluation orchestration (qa/arena/rag — heavily triplicated), agent chat loop, dataset import, run-and-wait, rubric (rubric-kit), artifacts, provider/judge utils | |
| `adapters/` | base ABC, factory, registry, litellm_judge | "pluggable evaluator" machinery with exactly **one** adapter | `supports_mode`/`get_available_metrics` have zero callers |
| `agent_backends/` | base, factory, litellm_agent, custom_httpx_agent | streaming chat backends | |
| `rag_backends/` | base, factory, http_adapter, pgvector_adapter | RAG retrieval+generation | pgvector behind optional `asyncpg` extra |
| `harnesses/` | base, registry, factory, builtin, subprocess_harness, parsers/{base,goose} | external CLI agent support | `BuiltinHarness` is self-described dead code |
| `mcp/` | client, manager | MCP stdio JSON-RPC client + per-session manager | |
| `environments/` | base ABC, byoe | environment provisioning | **All stubs/TODOs** |
| `websocket/` | progress, chat | `/ws/progress/{eval_id}`, `/ws/session/{session_id}` | No auth, no origin check |

## Runtime topology

- Dev: uvicorn :8000 (auto-reload) + Vite :5173 (proxy `/api`, `/ws` → 8000 per `vite.config.ts`), launched by `make dev` *or* `dev.sh` (two parallel launchers).
- Prod (per compose.prod): single backend container (uvicorn) + nginx :80 proxying everything to backend, including `/` — but the backend has **no StaticFiles mount**, so the UI built into the image is never served.
- DB: SQLite via aiosqlite, WAL pragma on connect. Schema created **only** by manual `alembic upgrade head`; no startup migration hook anywhere.
- LLM access: `litellm.acompletion` (judge + builtin agent + qa model calls), raw `httpx` for "custom" providers and RAG HTTP backends, `asyncpg` for pgvector.
- Background work: `asyncio.create_task` with module-level strong-ref set in `api/v1/evaluations.py`; one fresh `AsyncSession` per run.

## Data flow per evaluation mode

- **Q&A**: POST /evaluations (config: model_endpoint, judge_config, model_params, judge_params, evaluator_id*) → FE immediately POSTs /{id}/rerun → `run_qa_evaluation`: per item `call_model()` then `LiteLLMJudgeAdapter.evaluate_qa()`; results + WS progress/logs; artifacts (results.json/summary.md/config.json). *`evaluator_id` is never read by the backend.*
- **Arena**: same skeleton with `config.contestants[]`; per contestant×item; leaderboard via GET /results/arena/{id}.
- **RAG**: same skeleton; per item `rag_adapter.retrieve_and_generate()` then `evaluate_rag()` (4 fixed metrics via a single judge call).
- **Agent**: Session row + WS `/ws/session/{id}`; `process_user_message` agentic loop (LiteLLM streaming or subprocess harness, MCP tools); explicit scoring via POST /sessions/{id}/score → `evaluate_conversation`.

## Storage inventory

- SQLite tables: evaluations, judge_configs, datasets, dataset_items, results, sessions, artifacts, api_keys, rubrics, environments (unused), providers (**dead**).
- YAML files (read/written at runtime by API): `config/providers.yaml`, `config/tool_servers.yaml`, `config/harnesses.yaml` (path resolution buggy), `config/evaluators.yaml` (read-only).
- Filesystem: `backend/data/artifacts/{evaluation_id}/...`, `config/evaluators/{evaluator_id}/...` uploaded config files.
- In-memory: dataset import analysis sessions (15-min TTL, full file rows), WS connection maps, per-session MCP managers.

## Dependencies

Backend (`backend/pyproject.toml`): fastapi 0.115.x, uvicorn 0.32.x, sqlalchemy[asyncio] 2.0, aiosqlite, alembic 1.14, pydantic 2, pydantic-settings, litellm 1.4x, structlog, **asyncssh (only imported by the stub BYOE provider)**, python-multipart, httpx 0.27, pyyaml, rubric-kit ≥0.2; dev: pytest(+asyncio,+cov), ruff, **mkdocs-material (doc tool living in backend deps)**; extra: asyncpg.

Frontend (`frontend/package.json`): react 19, react-router-dom 7, zustand 5, tailwind 4 + shadcn stack (radix), recharts, @tanstack/react-table, sonner, react-markdown + rehype-sanitize, jspdf + jspdf-autotable + html2canvas-pro (PDF export), yaml, zod + react-hook-form + @hookform/resolvers (**used by exactly one component — every other form is hand-rolled state**), next-themes.

Clients (`clients/pyproject.toml`): httpx, pydantic; cli extra: typer, rich; dev: pytest, respx.

## Size hot spots

- `agent_chat_service.py` ≈ 583 lines (one generator function ≈ 380 lines).
- Three eval services ≈ 1,030 lines total, ~85% structurally identical.
- `AgentEvaluation.tsx` 521 lines; four evaluate pages share a configure/running/complete skeleton.
- 22 alembic migrations including 2 merge revisions; ≥6 migrations exist solely for the dead `providers` table.
