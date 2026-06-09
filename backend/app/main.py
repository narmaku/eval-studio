import uuid
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.core.config import settings
from app.core.exceptions import AppException
from app.core.logging import configure_logging, get_logger
from app.schemas.common import ProblemDetail


async def _migrate_scored_sessions() -> None:
    """Fix legacy sessions that were auto-scored but left with status 'ended'."""
    from sqlalchemy import text

    from app.core.database import async_session_factory

    async with async_session_factory() as db:
        result = await db.execute(
            text(
                "UPDATE sessions SET status = 'completed' "
                "WHERE status = 'ended' AND scores IS NOT NULL AND scores != 'null' AND length(scores) > 4"
            )
        )
        if result.rowcount:
            logger = get_logger("app.main")
            logger.info("Migrated legacy scored sessions", count=result.rowcount)
        await db.commit()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan: startup and shutdown events."""
    configure_logging()
    logger = get_logger("app.main")
    logger.info(
        "Starting eval-studio backend",
        version=settings.app_version,
        debug=settings.debug,
    )
    if settings.auth_disabled:
        logger.warning("Authentication is DISABLED (AUTH_DISABLED=true). All endpoints are publicly accessible.")
    await _migrate_scored_sessions()
    yield
    logger = get_logger("app.main")
    logger.info("Shutting down eval-studio backend")


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
    return JSONResponse(
        status_code=422,
        content=ProblemDetail(
            type="about:blank",
            title="Validation Error",
            status=422,
            detail=str(exc.errors()),
            instance=str(request.url),
        ).model_dump(),
    )


# Import and include routers
from app.api.v1.api_keys import router as api_keys_router  # noqa: E402
from app.api.v1.artifacts import router as artifacts_router  # noqa: E402
from app.api.v1.dataset_import import router as dataset_import_router  # noqa: E402
from app.api.v1.datasets import router as datasets_router  # noqa: E402
from app.api.v1.environments import router as environments_router  # noqa: E402
from app.api.v1.evaluations import router as evaluations_router  # noqa: E402
from app.api.v1.evaluators import router as evaluators_router  # noqa: E402
from app.api.v1.harnesses import router as harnesses_router  # noqa: E402
from app.api.v1.health import router as health_router  # noqa: E402
from app.api.v1.judges import router as judges_router  # noqa: E402
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
app.include_router(environments_router, prefix="/api/v1")
app.include_router(judges_router, prefix="/api/v1")
app.include_router(providers_router, prefix="/api/v1")
app.include_router(rubrics_router, prefix="/api/v1")
app.include_router(results_router, prefix="/api/v1")
app.include_router(tool_servers_router, prefix="/api/v1")
app.include_router(harnesses_router, prefix="/api/v1")
app.include_router(ws_chat_router)
app.include_router(ws_progress_router)
