from contextlib import ExitStack

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import event
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.adapters.registry import evaluator_registry
from app.core.config import settings
from app.core.database import Base, get_db
from app.core.providers import ProviderProfile, provider_registry
from app.core.tool_servers import tool_server_registry
from app.harnesses.registry import harness_registry
from app.main import app

TEST_DATABASE_URL = "sqlite+aiosqlite://"  # in-memory


@pytest.fixture(autouse=True)
def _disable_auth():
    """Disable authentication for all tests by default.

    Tests that need to exercise auth behaviour should override this
    by setting ``settings.auth_disabled = False`` explicitly.
    """
    original = settings.auth_disabled
    settings.auth_disabled = True
    yield
    settings.auth_disabled = original


@pytest.fixture
async def async_engine():
    engine = create_async_engine(TEST_DATABASE_URL, echo=False)

    @event.listens_for(engine.sync_engine, "connect")
    def _set_sqlite_pragma(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest.fixture
async def db_session(async_engine):
    session_factory = async_sessionmaker(async_engine, class_=AsyncSession, expire_on_commit=False)
    async with session_factory() as session:
        yield session


@pytest.fixture
async def client(async_engine):
    session_factory = async_sessionmaker(async_engine, class_=AsyncSession, expire_on_commit=False)

    async def override_get_db():
        async with session_factory() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()


@pytest.fixture(autouse=True)
def _isolate_yaml_registries(tmp_path):
    """Redirect ALL YAML-backed registry singletons to temp paths.

    Prevents tests from reading or writing real config/*.yaml files.
    Integration tests that need seeded data add their own fixtures on top.
    """
    registries = [provider_registry, tool_server_registry, harness_registry, evaluator_registry]

    with ExitStack() as stack:
        for registry in registries:
            config_name = registry._config_path.name if registry._config_path else "config.yaml"
            stack.enter_context(registry.isolated(tmp_path / config_name))

        # Seed a minimal test judge provider (many evaluation tests need one)
        # and persist so _check_reload() doesn't wipe it when the file is missing
        provider_registry._items["__test__"] = ProviderProfile(
            id="__test__",
            name="Test Judge",
            default_model="test-judge-model",
        )
        provider_registry._persist_yaml()

        yield
