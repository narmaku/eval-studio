"""Boot test: verify the app starts against a fresh empty database.

Exercises the real lifespan (Alembic migrations on an empty file-backed
SQLite) and confirms the health endpoint responds.  No mocking.
"""

import os
import tempfile
from unittest.mock import patch

import pytest
from httpx import ASGITransport, AsyncClient


@pytest.mark.asyncio
async def test_fresh_db_boot_and_health():
    """App boots against an empty database, runs migrations, serves /health."""
    with tempfile.TemporaryDirectory() as tmp:
        db_path = os.path.join(tmp, "test_boot.db")
        db_url = f"sqlite+aiosqlite:///{db_path}"

        with patch("app.core.config.settings.database_url", db_url):
            # Re-create engine pointing at the temp DB so get_db() uses it.
            from sqlalchemy import event
            from sqlalchemy.ext.asyncio import (
                AsyncSession,
                async_sessionmaker,
                create_async_engine,
            )

            import app.core.database as db_mod
            from app.main import app

            test_engine = create_async_engine(db_url, echo=False)

            @event.listens_for(test_engine.sync_engine, "connect")
            def _set_pragma(dbapi_conn, _rec):
                cur = dbapi_conn.cursor()
                cur.execute("PRAGMA foreign_keys=ON")
                cur.close()

            test_factory = async_sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)

            orig_engine = db_mod.engine
            orig_factory = db_mod.async_session_factory
            db_mod.engine = test_engine
            db_mod.async_session_factory = test_factory

            try:
                # Run the lifespan — this triggers Alembic migrations
                async with app.router.lifespan_context(app):
                    # DB file should now exist with tables
                    assert os.path.exists(db_path), "Database file was not created"

                    async with AsyncClient(
                        transport=ASGITransport(app=app),
                        base_url="http://test",
                    ) as client:
                        resp = await client.get("/api/v1/health")
                        assert resp.status_code == 200
                        body = resp.json()
                        assert body["status"] == "healthy"
            finally:
                db_mod.engine = orig_engine
                db_mod.async_session_factory = orig_factory
                await test_engine.dispose()


@pytest.mark.asyncio
async def test_fresh_db_tables_created_by_migration():
    """After boot, all expected tables exist in the migrated database."""
    with tempfile.TemporaryDirectory() as tmp:
        db_path = os.path.join(tmp, "test_tables.db")
        db_url = f"sqlite+aiosqlite:///{db_path}"

        with patch("app.core.config.settings.database_url", db_url):
            from sqlalchemy import text
            from sqlalchemy.ext.asyncio import (
                AsyncSession,
                async_sessionmaker,
                create_async_engine,
            )

            import app.core.database as db_mod
            from app.main import app

            test_engine = create_async_engine(db_url, echo=False)
            test_factory = async_sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)

            orig_engine = db_mod.engine
            orig_factory = db_mod.async_session_factory
            db_mod.engine = test_engine
            db_mod.async_session_factory = test_factory

            try:
                async with app.router.lifespan_context(app):
                    async with test_engine.connect() as conn:
                        result = await conn.execute(
                            text("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
                        )
                        tables = {row[0] for row in result.fetchall()}

                    expected = {
                        "alembic_version",
                        "evaluations",
                        "datasets",
                        "dataset_items",
                        "results",
                        "sessions",
                        "artifacts",
                        "rubrics",
                        "api_keys",
                    }
                    assert expected.issubset(tables), f"Missing tables: {expected - tables}"
            finally:
                db_mod.engine = orig_engine
                db_mod.async_session_factory = orig_factory
                await test_engine.dispose()
