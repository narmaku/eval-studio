import asyncio
import uuid
from contextlib import asynccontextmanager
from pathlib import Path

import structlog
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.core.config import settings
from app.core.exceptions import AppException
from app.core.logging import configure_logging, get_logger
from app.schemas.common import ProblemDetail


def _run_alembic_migrations() -> None:
    """Run Alembic migrations to head (creates tables on fresh DB, applies pending migrations).

    Runs synchronously — call via asyncio.to_thread from the async lifespan
    because alembic's env.py uses asyncio.run internally.
    """
    from alembic.config import Config

    from alembic import command

    backend_dir = Path(__file__).resolve().parents[1]
    cfg = Config(str(backend_dir / "alembic.ini"))
    cfg.set_main_option("script_location", str(backend_dir / "alembic"))
    command.upgrade(cfg, "head")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan: startup and shutdown events."""
    configure_logging()
    logger = get_logger("app.main")
    logger.info(
        "app.startup",
        version=settings.app_version,
        debug=settings.debug,
    )
    if settings.auth_disabled:
        logger.warning("app.auth_disabled")
    if not settings.database_url.endswith("://"):
        await asyncio.to_thread(_run_alembic_migrations)
    yield
    logger = get_logger("app.main")
    logger.info("app.shutdown")


app = FastAPI(
    title="eval-studio",
    version=settings.app_version,
    docs_url="/docs",
    openapi_url="/api/v1/openapi.json",
    lifespan=lifespan,
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Correlation ID middleware
@app.middleware("http")
async def correlation_id_middleware(request: Request, call_next):
    request_id = request.headers.get("x-request-id", str(uuid.uuid4()))
    structlog.contextvars.clear_contextvars()
    structlog.contextvars.bind_contextvars(request_id=request_id)
    response = await call_next(request)
    response.headers["X-Request-ID"] = request_id
    return response


# RFC 7807 exception handlers
@app.exception_handler(AppException)
async def app_exception_handler(request: Request, exc: AppException) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content=ProblemDetail(
            type=exc.type_uri,
            title=exc.title,
            status=exc.status_code,
            detail=exc.detail,
            instance=str(request.url),
        ).model_dump(),
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    structured = [{"loc": list(e["loc"]), "msg": e["msg"], "type": e["type"]} for e in exc.errors()]
    return JSONResponse(
        status_code=422,
        content=ProblemDetail(
            type="about:blank",
            title="Validation Error",
            status=422,
            detail="Request validation failed",
            instance=str(request.url),
            errors=structured,
        ).model_dump(),
    )


# Import and include routers
from app.api.v1.api_keys import router as api_keys_router  # noqa: E402
from app.api.v1.artifacts import router as artifacts_router  # noqa: E402
from app.api.v1.dataset_import import router as dataset_import_router  # noqa: E402
from app.api.v1.datasets import router as datasets_router  # noqa: E402
from app.api.v1.evaluations import router as evaluations_router  # noqa: E402
from app.api.v1.evaluators import router as evaluators_router  # noqa: E402
from app.api.v1.harnesses import router as harnesses_router  # noqa: E402
from app.api.v1.health import router as health_router  # noqa: E402
from app.api.v1.providers import router as providers_router  # noqa: E402
from app.api.v1.results import router as results_router  # noqa: E402
from app.api.v1.rubrics import router as rubrics_router  # noqa: E402
from app.api.v1.sessions import router as sessions_router  # noqa: E402
from app.api.v1.tool_servers import router as tool_servers_router  # noqa: E402
from app.websocket.chat import router as ws_chat_router  # noqa: E402
from app.websocket.progress import router as ws_progress_router  # noqa: E402

app.include_router(health_router, prefix="/api/v1")
app.include_router(api_keys_router, prefix="/api/v1")
app.include_router(artifacts_router, prefix="/api/v1")
app.include_router(dataset_import_router, prefix="/api/v1")
app.include_router(datasets_router, prefix="/api/v1")
app.include_router(evaluations_router, prefix="/api/v1")
app.include_router(evaluators_router, prefix="/api/v1")
app.include_router(sessions_router, prefix="/api/v1")
app.include_router(providers_router, prefix="/api/v1")
app.include_router(rubrics_router, prefix="/api/v1")
app.include_router(results_router, prefix="/api/v1")
app.include_router(tool_servers_router, prefix="/api/v1")
app.include_router(harnesses_router, prefix="/api/v1")
app.include_router(ws_chat_router)
app.include_router(ws_progress_router)

# --- Production SPA serving ---
# In production (Containerfile), the frontend build is copied to /app/static/.
# Mount /assets for hashed static assets and add a catch-all SPA fallback.
# Guarded by is_dir() so dev runs without a frontend build are unaffected.
_static = Path(__file__).resolve().parents[1] / "static"
if _static.is_dir():
    from fastapi.responses import FileResponse
    from fastapi.staticfiles import StaticFiles

    app.mount("/assets", StaticFiles(directory=_static / "assets"), name="assets")

    @app.get("/{full_path:path}", include_in_schema=False)
    async def spa(full_path: str):
        candidate = _static / full_path
        if full_path and candidate.is_file():
            return FileResponse(candidate)
        return FileResponse(_static / "index.html")
