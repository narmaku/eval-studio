import asyncio
import time
from contextlib import asynccontextmanager
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.providers import ProviderProfile, provider_registry


def _make_mock_call_model():
    """Return a mock that simulates call_model() returning plain text."""

    async def mock_call_model(resolved, question, **kwargs):
        return "This is the model's answer."

    return mock_call_model


async def _wait_for_completion(client, evaluation_id: str, timeout: float = 10.0) -> dict:
    """Poll evaluation status until completed or timeout."""
    start = time.monotonic()
    while time.monotonic() - start < timeout:
        resp = await client.get(f"/api/v1/evaluations/{evaluation_id}")
        data = resp.json()
        if data["status"] in ("completed", "failed"):
            return data
        await asyncio.sleep(0.1)
    raise TimeoutError(f"Evaluation {evaluation_id} did not complete within {timeout}s")


@pytest.fixture
def mock_bg_session_factory(async_engine):
    """Create a session factory that uses the test database engine."""
    factory = async_sessionmaker(async_engine, class_=AsyncSession, expire_on_commit=False)

    @asynccontextmanager
    async def ctx():
        async with factory() as session:
            yield session

    return ctx


@pytest.fixture(autouse=True)
def _register_test_judge_provider():
    provider_registry._items["__test__"] = ProviderProfile(
        id="__test__",
        name="Test Judge",
        default_model="test-judge-model",
    )
    yield
    provider_registry._items.pop("__test__", None)


@pytest.mark.asyncio
async def test_full_qa_evaluation_flow(client, mock_bg_session_factory):
    """End-to-end Q&A evaluation through HTTP endpoints."""
    # 1. Create dataset with Q&A items
    dataset_payload = {
        "name": "Test Dataset",
        "items": [
            {"question": "What is RHEL?", "expected_answer": "Red Hat Enterprise Linux"},
            {"question": "What is Fedora?", "expected_answer": "A Linux distribution"},
            {"question": "What is Podman?", "expected_answer": "A container engine"},
        ],
    }
    dataset_resp = await client.post("/api/v1/datasets", json=dataset_payload)
    assert dataset_resp.status_code == 201
    dataset_id = dataset_resp.json()["id"]

    # 2. Create evaluation
    eval_payload = {
        "name": "Flow Test Eval",
        "mode": "qa",
        "dataset_id": dataset_id,
        "config": {
            "model_endpoint": {"default_model": "test-model"},
            "judge_config": {"provider_id": "__test__"},
        },
    }
    eval_resp = await client.post("/api/v1/evaluations", json=eval_payload)
    assert eval_resp.status_code == 201
    eval_id = eval_resp.json()["id"]

    # 4. Run the evaluation (with mocked LLM and session factory)
    with (
        patch("app.services.eval_runner.call_model", side_effect=_make_mock_call_model()),
        patch("app.adapters.litellm_judge.litellm.acompletion", new_callable=AsyncMock) as mock_judge,
        patch("app.services.eval_runner.broadcast_progress", new_callable=AsyncMock),
        patch("app.api.v1.evaluations.async_session_factory", mock_bg_session_factory),
    ):
        mock_judge.return_value = MagicMock(
            choices=[MagicMock(message=MagicMock(content='{"score": 0.85, "reasoning": "Good answer"}'))]
        )

        run_resp = await client.post(f"/api/v1/evaluations/{eval_id}/run")
        assert run_resp.status_code == 200

        # 5. Wait for completion
        eval_data = await _wait_for_completion(client, eval_id)
        assert eval_data["status"] == "completed"

    # 6. Check results
    results_resp = await client.get("/api/v1/results", params={"evaluation_id": eval_id})
    assert results_resp.status_code == 200
    results_data = results_resp.json()
    assert results_data["total"] == 3

    # 7. Verify result fields
    for item in results_data["items"]:
        assert item["score"] == 0.85
        assert item["passed"] is True
        assert item["actual_answer"] is not None


@pytest.mark.asyncio
async def test_rerun_evaluation(client, mock_bg_session_factory):
    """Run an evaluation, then rerun, verifying old results are cleared."""
    # Create dataset
    dataset_resp = await client.post(
        "/api/v1/datasets",
        json={"name": "Rerun Dataset", "items": [{"question": "Q1", "expected_answer": "A1"}]},
    )
    dataset_id = dataset_resp.json()["id"]

    # Create evaluation
    eval_resp = await client.post(
        "/api/v1/evaluations",
        json={
            "name": "Rerun Eval",
            "mode": "qa",
            "dataset_id": dataset_id,
            "config": {
                "model_endpoint": {"default_model": "test-model"},
                "judge_config": {"provider_id": "__test__"},
            },
        },
    )
    eval_id = eval_resp.json()["id"]

    mock_call = AsyncMock(return_value="answer")
    mock_judge = AsyncMock(
        return_value=MagicMock(choices=[MagicMock(message=MagicMock(content='{"score": 0.9, "reasoning": "OK"}'))]),
    )

    with (
        patch("app.services.eval_runner.call_model", mock_call),
        patch("app.adapters.litellm_judge.litellm.acompletion", mock_judge),
        patch("app.services.eval_runner.broadcast_progress", new_callable=AsyncMock),
        patch("app.api.v1.evaluations.async_session_factory", mock_bg_session_factory),
    ):
        # First run
        await client.post(f"/api/v1/evaluations/{eval_id}/run")
        await _wait_for_completion(client, eval_id)

        # Verify first run results
        results_resp = await client.get("/api/v1/results", params={"evaluation_id": eval_id})
        assert results_resp.json()["total"] == 1

        # Rerun
        rerun_resp = await client.post(f"/api/v1/evaluations/{eval_id}/rerun")
        assert rerun_resp.status_code == 200

        await _wait_for_completion(client, eval_id)

    # Verify new results exist (old ones cleared)
    results_resp = await client.get("/api/v1/results", params={"evaluation_id": eval_id})
    assert results_resp.json()["total"] == 1


@pytest.mark.asyncio
async def test_run_evaluation_not_found(client):
    """POST /evaluations/nonexistent/run returns 404."""
    response = await client.post("/api/v1/evaluations/nonexistent-id/run")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_run_evaluation_wrong_mode(client):
    """Create an agent mode evaluation, POST /run returns 501."""
    eval_resp = await client.post(
        "/api/v1/evaluations",
        json={"name": "Agent Eval", "mode": "agent"},
    )
    eval_id = eval_resp.json()["id"]

    run_resp = await client.post(f"/api/v1/evaluations/{eval_id}/run")
    assert run_resp.status_code == 501
