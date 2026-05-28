"""Integration tests for the Rubrics CRUD API."""

import pytest

RUBRIC_PAYLOAD = {
    "name": "Test Rubric",
    "description": "A test rubric",
    "dimensions": [
        {"name": "accuracy", "weight": 0.6, "description": "How accurate is the answer"},
        {"name": "completeness", "weight": 0.4, "description": "How complete is the answer"},
    ],
    "pass_threshold": 0.8,
    "aggregation": "weighted_average",
    "prompt_template": "Rate the following: {response}",
}


@pytest.mark.asyncio
async def test_create_rubric(client):
    """POST /rubrics creates a rubric and returns 201."""
    response = await client.post("/api/v1/rubrics", json=RUBRIC_PAYLOAD)
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Test Rubric"
    assert data["description"] == "A test rubric"
    assert len(data["dimensions"]) == 2
    assert data["dimensions"][0]["name"] == "accuracy"
    assert data["dimensions"][0]["weight"] == 0.6
    assert data["pass_threshold"] == 0.8
    assert data["aggregation"] == "weighted_average"
    assert data["prompt_template"] == "Rate the following: {response}"
    assert data["id"] is not None
    assert data["created_at"] is not None
    assert data["updated_at"] is not None


@pytest.mark.asyncio
async def test_create_rubric_minimal(client):
    """POST /rubrics with minimal payload uses correct defaults."""
    payload = {
        "name": "Minimal Rubric",
        "dimensions": [{"name": "quality", "weight": 1.0, "description": "Overall quality"}],
    }
    response = await client.post("/api/v1/rubrics", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Minimal Rubric"
    assert data["description"] is None
    assert data["pass_threshold"] == 0.7
    assert data["aggregation"] == "weighted_average"
    assert data["prompt_template"] is None


@pytest.mark.asyncio
async def test_create_rubric_empty_dimensions_rejected(client):
    """POST /rubrics with empty dimensions returns 422."""
    payload = {"name": "Bad Rubric", "dimensions": []}
    response = await client.post("/api/v1/rubrics", json=payload)
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_create_rubric_negative_weight_rejected(client):
    """POST /rubrics with negative weight returns 422."""
    payload = {
        "name": "Bad Rubric",
        "dimensions": [{"name": "accuracy", "weight": -1.0, "description": "bad"}],
    }
    response = await client.post("/api/v1/rubrics", json=payload)
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_list_rubrics_empty(client):
    """GET /rubrics when empty returns empty paginated response."""
    response = await client.get("/api/v1/rubrics")
    assert response.status_code == 200
    data = response.json()
    assert data["items"] == []
    assert data["total"] == 0
    assert data["pages"] == 1


@pytest.mark.asyncio
async def test_list_rubrics_pagination(client):
    """Create 3 rubrics, verify pagination works."""
    for i in range(3):
        payload = {
            "name": f"Rubric {i}",
            "dimensions": [{"name": "quality", "weight": 1.0, "description": "Quality"}],
        }
        await client.post("/api/v1/rubrics", json=payload)

    response = await client.get("/api/v1/rubrics", params={"page": 1, "page_size": 2})
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 3
    assert data["pages"] == 2
    assert len(data["items"]) == 2


@pytest.mark.asyncio
async def test_list_rubrics_name_filter(client):
    """Filter rubrics by name substring."""
    await client.post(
        "/api/v1/rubrics",
        json={"name": "Alpha Rubric", "dimensions": [{"name": "q", "weight": 1.0, "description": "q"}]},
    )
    await client.post(
        "/api/v1/rubrics",
        json={"name": "Beta Rubric", "dimensions": [{"name": "q", "weight": 1.0, "description": "q"}]},
    )

    response = await client.get("/api/v1/rubrics", params={"name": "alpha"})
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 1
    assert data["items"][0]["name"] == "Alpha Rubric"


@pytest.mark.asyncio
async def test_get_rubric(client):
    """GET /rubrics/{id} returns the rubric."""
    create_resp = await client.post("/api/v1/rubrics", json=RUBRIC_PAYLOAD)
    rubric_id = create_resp.json()["id"]

    response = await client.get(f"/api/v1/rubrics/{rubric_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == rubric_id
    assert data["name"] == "Test Rubric"


@pytest.mark.asyncio
async def test_get_rubric_not_found(client):
    """GET /rubrics/nonexistent returns 404."""
    response = await client.get("/api/v1/rubrics/nonexistent-id")
    assert response.status_code == 404
    data = response.json()
    assert data["title"] == "Not Found"
    assert "nonexistent-id" in data["detail"]


@pytest.mark.asyncio
async def test_update_rubric(client):
    """PUT /rubrics/{id} updates fields."""
    create_resp = await client.post("/api/v1/rubrics", json=RUBRIC_PAYLOAD)
    rubric_id = create_resp.json()["id"]

    update_payload = {"name": "Updated Rubric", "pass_threshold": 0.9}
    response = await client.put(f"/api/v1/rubrics/{rubric_id}", json=update_payload)
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Updated Rubric"
    assert data["pass_threshold"] == 0.9
    # Unchanged fields should remain
    assert data["description"] == "A test rubric"
    assert len(data["dimensions"]) == 2


@pytest.mark.asyncio
async def test_update_rubric_not_found(client):
    """PUT /rubrics/nonexistent returns 404."""
    response = await client.put("/api/v1/rubrics/nonexistent-id", json={"name": "Fail"})
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_delete_rubric(client):
    """DELETE /rubrics/{id} removes the rubric."""
    create_resp = await client.post("/api/v1/rubrics", json=RUBRIC_PAYLOAD)
    rubric_id = create_resp.json()["id"]

    response = await client.delete(f"/api/v1/rubrics/{rubric_id}")
    assert response.status_code == 204

    # Verify it's gone
    get_resp = await client.get(f"/api/v1/rubrics/{rubric_id}")
    assert get_resp.status_code == 404


@pytest.mark.asyncio
async def test_delete_rubric_not_found(client):
    """DELETE /rubrics/nonexistent returns 404."""
    response = await client.delete("/api/v1/rubrics/nonexistent-id")
    assert response.status_code == 404
