"""Integration tests for POST /api/v1/evaluations/run (run-and-wait endpoint)."""

from contextlib import asynccontextmanager
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker


@pytest.fixture
def mock_bg_session_factory(async_engine):
    """Create a session factory (async context manager) that uses the test database."""
    factory = async_sessionmaker(async_engine, class_=AsyncSession, expire_on_commit=False)

    @asynccontextmanager
    async def ctx():
        async with factory() as session:
            yield session

    return ctx


@pytest.fixture
async def dataset_id(client):
    """Create a dataset and return its ID."""
    resp = await client.post(
        "/api/v1/datasets",
        json={
            "name": "Run Test Dataset",
            "items": [
                {"question": "What is RHEL?", "expected_answer": "Red Hat Enterprise Linux"},
                {"question": "What is Podman?", "expected_answer": "A container engine"},
            ],
        },
    )
    assert resp.status_code == 201
    return resp.json()["id"]


@pytest.fixture
async def judge_config_id(client):
    """Create a judge config and return its ID."""
    resp = await client.post(
        "/api/v1/judges",
        json={"name": "Test Judge", "model": "test-model", "pass_threshold": 0.7},
    )
    assert resp.status_code == 201
    return resp.json()["id"]


# ── Sync run ────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_run_sync_qa(client, dataset_id, judge_config_id, mock_bg_session_factory):
    """POST /evaluations/run with QA mode returns complete RunResponse with results."""
    mock_call = AsyncMock(return_value="Test answer")
    mock_judge = AsyncMock(
        return_value=MagicMock(choices=[MagicMock(message=MagicMock(content='{"score": 0.85, "reasoning": "Good"}'))]),
    )

    with (
        patch("app.services.evaluation_service.call_model", mock_call),
        patch("app.adapters.litellm_judge.litellm.acompletion", mock_judge),
        patch("app.services.evaluation_service.broadcast_progress", new_callable=AsyncMock),
        patch("app.services.run_service.async_session_factory", mock_bg_session_factory),
    ):
        resp = await client.post(
            "/api/v1/evaluations/run",
            json={
                "name": "Sync QA Run",
                "mode": "qa",
                "dataset_id": dataset_id,
                "judge_config_id": judge_config_id,
                "config": {"model": "test-model"},
                "pass_threshold": 0.7,
            },
        )

    assert resp.status_code == 200
    data = resp.json()
    assert data["verdict"] in ("pass", "fail")
    assert data["exit_code"] in (0, 1)
    assert data["total_items"] == 2
    assert data["evaluation_id"]
    assert data["status"] == "completed"
    assert data["mode"] == "qa"
    assert data["pass_threshold"] == 0.7
    assert data["duration_seconds"] > 0
    assert len(data["results"]) == 2
    # With score 0.85, it should pass with threshold 0.7
    assert data["verdict"] == "pass"
    assert data["exit_code"] == 0


# ── Async mode ──────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_run_async_mode(client, dataset_id, mock_bg_session_factory):
    """POST /evaluations/run?async=true returns 202 with RunAsyncResponse."""
    with (
        patch("app.services.evaluation_service.call_model", new_callable=AsyncMock, return_value="answer"),
        patch(
            "app.adapters.litellm_judge.litellm.acompletion",
            new_callable=AsyncMock,
            return_value=MagicMock(choices=[MagicMock(message=MagicMock(content='{"score": 0.9, "reasoning": "OK"}'))]),
        ),
        patch("app.services.evaluation_service.broadcast_progress", new_callable=AsyncMock),
        patch("app.api.v1.evaluations.async_session_factory", mock_bg_session_factory),
    ):
        resp = await client.post(
            "/api/v1/evaluations/run",
            params={"async": "true"},
            json={
                "name": "Async QA Run",
                "mode": "qa",
                "dataset_id": dataset_id,
                "config": {"model": "test-model"},
            },
        )

    assert resp.status_code == 202
    data = resp.json()
    assert data["status"] == "running"
    assert data["evaluation_id"]
    assert data["poll_url"].startswith("/api/v1/evaluations/")


# ── Timeout cap ─────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_run_timeout_capped(client, dataset_id):
    """timeout > run_timeout_max returns 422 validation error."""
    resp = await client.post(
        "/api/v1/evaluations/run",
        params={"timeout": 99999},
        json={
            "name": "Timeout Test",
            "mode": "qa",
            "dataset_id": dataset_id,
        },
    )
    assert resp.status_code == 422


# ── Plain text response ─────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_run_plain_text_response(client, dataset_id, judge_config_id, mock_bg_session_factory):
    """Accept: text/plain returns 'score\\nVERDICT' format."""
    mock_call = AsyncMock(return_value="Test answer")
    mock_judge = AsyncMock(
        return_value=MagicMock(choices=[MagicMock(message=MagicMock(content='{"score": 0.85, "reasoning": "Good"}'))]),
    )

    with (
        patch("app.services.evaluation_service.call_model", mock_call),
        patch("app.adapters.litellm_judge.litellm.acompletion", mock_judge),
        patch("app.services.evaluation_service.broadcast_progress", new_callable=AsyncMock),
        patch("app.services.run_service.async_session_factory", mock_bg_session_factory),
    ):
        resp = await client.post(
            "/api/v1/evaluations/run",
            json={
                "name": "Plain Text Run",
                "mode": "qa",
                "dataset_id": dataset_id,
                "judge_config_id": judge_config_id,
                "config": {"model": "test-model"},
                "pass_threshold": 0.7,
            },
            headers={"Accept": "text/plain"},
        )

    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith("text/plain")
    lines = resp.text.strip().split("\n")
    assert len(lines) == 2
    score = float(lines[0])
    assert 0.0 <= score <= 1.0
    assert lines[1] in ("PASS", "FAIL")


# ── Invalid dataset ─────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_run_invalid_dataset(client):
    """returns 404 for nonexistent dataset_id."""
    resp = await client.post(
        "/api/v1/evaluations/run",
        json={
            "name": "Bad Dataset Run",
            "mode": "qa",
            "dataset_id": "nonexistent-dataset-id",
        },
    )
    assert resp.status_code == 404


# ── Missing required fields ─────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_run_missing_required_fields(client):
    """returns 422 for missing name/mode/dataset_id."""
    resp = await client.post(
        "/api/v1/evaluations/run",
        json={},
    )
    assert resp.status_code == 422


# ── pass_threshold validation ───────────────────────────────────────────────


@pytest.mark.asyncio
async def test_run_pass_threshold_out_of_range(client, dataset_id):
    """pass_threshold > 1 returns 422 validation error."""
    resp = await client.post(
        "/api/v1/evaluations/run",
        json={
            "name": "Bad Threshold Run",
            "mode": "qa",
            "dataset_id": dataset_id,
            "pass_threshold": 1.5,
        },
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_run_pass_threshold_negative(client, dataset_id):
    """pass_threshold < 0 returns 422 validation error."""
    resp = await client.post(
        "/api/v1/evaluations/run",
        json={
            "name": "Negative Threshold Run",
            "mode": "qa",
            "dataset_id": dataset_id,
            "pass_threshold": -0.1,
        },
    )
    assert resp.status_code == 422


# ── timeout lower bound ────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_run_timeout_zero_rejected(client, dataset_id):
    """timeout=0 returns 422 validation error."""
    resp = await client.post(
        "/api/v1/evaluations/run",
        params={"timeout": 0},
        json={
            "name": "Zero Timeout Run",
            "mode": "qa",
            "dataset_id": dataset_id,
        },
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_run_timeout_negative_rejected(client, dataset_id):
    """timeout=-1 returns 422 validation error."""
    resp = await client.post(
        "/api/v1/evaluations/run",
        params={"timeout": -1},
        json={
            "name": "Negative Timeout Run",
            "mode": "qa",
            "dataset_id": dataset_id,
        },
    )
    assert resp.status_code == 422


# ── Arena validation ────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_run_arena_missing_contestants(client, dataset_id):
    """Arena mode without enough contestants returns 422 validation error."""
    resp = await client.post(
        "/api/v1/evaluations/run",
        json={
            "name": "Arena No Contestants",
            "mode": "arena",
            "dataset_id": dataset_id,
            "config": {},
        },
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_run_arena_one_contestant(client, dataset_id):
    """Arena mode with only 1 contestant returns 422 validation error."""
    resp = await client.post(
        "/api/v1/evaluations/run",
        json={
            "name": "Arena One Contestant",
            "mode": "arena",
            "dataset_id": dataset_id,
            "config": {"contestants": [{"model": "model-a"}]},
        },
    )
    assert resp.status_code == 422
