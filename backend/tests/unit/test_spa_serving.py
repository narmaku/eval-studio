"""Tests for production SPA serving (INFRA-001)."""

import pytest
from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from httpx import ASGITransport, AsyncClient


def _create_spa_app(static_dir):
    """Build a minimal FastAPI app with SPA serving pointed at *static_dir*."""
    app = FastAPI()

    @app.get("/api/v1/health")
    async def health():
        return {"status": "ok"}

    app.mount("/assets", StaticFiles(directory=static_dir / "assets"), name="assets")

    @app.get("/{full_path:path}", include_in_schema=False)
    async def spa(full_path: str):
        candidate = static_dir / full_path
        if full_path and candidate.is_file():
            return FileResponse(candidate)
        return FileResponse(static_dir / "index.html")

    return app


@pytest.fixture()
def static_dir(tmp_path):
    """Create a fake frontend build output tree."""
    index = tmp_path / "index.html"
    index.write_text("<!doctype html><html><body>eval-studio</body></html>")
    assets = tmp_path / "assets"
    assets.mkdir()
    (assets / "index-abc123.js").write_text("console.log('app')")
    (tmp_path / "vite.svg").write_text("<svg/>")
    return tmp_path


@pytest.fixture()
def spa_app(static_dir):
    return _create_spa_app(static_dir)


@pytest.mark.asyncio
async def test_root_returns_index_html(spa_app):
    async with AsyncClient(transport=ASGITransport(app=spa_app), base_url="http://test") as ac:
        resp = await ac.get("/")
    assert resp.status_code == 200
    assert "<!doctype html>" in resp.text


@pytest.mark.asyncio
async def test_deep_route_returns_index_html(spa_app):
    async with AsyncClient(transport=ASGITransport(app=spa_app), base_url="http://test") as ac:
        resp = await ac.get("/results")
    assert resp.status_code == 200
    assert "<!doctype html>" in resp.text


@pytest.mark.asyncio
async def test_nested_deep_route_returns_index_html(spa_app):
    async with AsyncClient(transport=ASGITransport(app=spa_app), base_url="http://test") as ac:
        resp = await ac.get("/results/abc-123")
    assert resp.status_code == 200
    assert "<!doctype html>" in resp.text


@pytest.mark.asyncio
async def test_existing_file_served_directly(spa_app):
    async with AsyncClient(transport=ASGITransport(app=spa_app), base_url="http://test") as ac:
        resp = await ac.get("/vite.svg")
    assert resp.status_code == 200
    assert "<svg/>" in resp.text


@pytest.mark.asyncio
async def test_hashed_asset_served_by_static_mount(spa_app):
    async with AsyncClient(transport=ASGITransport(app=spa_app), base_url="http://test") as ac:
        resp = await ac.get("/assets/index-abc123.js")
    assert resp.status_code == 200
    assert "console.log" in resp.text


@pytest.mark.asyncio
async def test_api_routes_not_caught_by_spa(spa_app):
    async with AsyncClient(transport=ASGITransport(app=spa_app), base_url="http://test") as ac:
        resp = await ac.get("/api/v1/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}
