import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.database import Base, get_db
from app.core.providers import ProviderProfile, provider_registry
from app.core.tool_servers import tool_server_registry
from app.harnesses.registry import harness_registry
from app.main import app

TEST_DATABASE_URL = "sqlite+aiosqlite://"  # in-memory


@pytest.fixture
async def async_engine():
    engine = create_async_engine(TEST_DATABASE_URL, echo=False)
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
    registries_info = [
        (provider_registry, "_providers"),
        (tool_server_registry, "_servers"),
        (harness_registry, "_harnesses"),
    ]
    originals = []
    for registry, dict_attr in registries_info:
        originals.append(
            {
                "registry": registry,
                "dict_attr": dict_attr,
                "data": getattr(registry, dict_attr).copy(),
                "config_path": registry._config_path,
                "last_mtime": registry._last_mtime,
            }
        )
        config_name = registry._config_path.name if registry._config_path else "config.yaml"
        registry._config_path = tmp_path / config_name
        getattr(registry, dict_attr).clear()
        registry._last_mtime = 0.0

    # Seed a minimal test judge provider (many evaluation tests need one)
    # and persist so _check_reload() doesn't wipe it when the file is missing
    provider_registry._providers["__test__"] = ProviderProfile(
        id="__test__",
        name="Test Judge",
        litellm_model="test-judge-model",
        purpose="judge",
    )
    provider_registry._persist_yaml()

    yield

    for orig in originals:
        reg = orig["registry"]
        attr = orig["dict_attr"]
        getattr(reg, attr).clear()
        getattr(reg, attr).update(orig["data"])
        reg._config_path = orig["config_path"]
        reg._last_mtime = orig["last_mtime"]
