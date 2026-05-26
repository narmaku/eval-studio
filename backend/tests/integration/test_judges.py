import pytest


@pytest.mark.asyncio
async def test_create_judge(client):
    """POST /judges with valid payload returns 201 and correct fields."""
    payload = {
        "name": "Test Judge",
        "model": "gpt-4.1",
        "temperature": 0.5,
        "pass_threshold": 0.8,
    }
    response = await client.post("/api/v1/judges", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Test Judge"
    assert data["model"] == "gpt-4.1"
    assert data["temperature"] == 0.5
    assert data["pass_threshold"] == 0.8
    assert data["id"] is not None
    assert data["created_at"] is not None


@pytest.mark.asyncio
async def test_create_judge_defaults(client):
    """POST /judges with minimal payload uses correct defaults."""
    payload = {"name": "Minimal Judge"}
    response = await client.post("/api/v1/judges", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Minimal Judge"
    assert data["model"] is None
    assert data["temperature"] == 0.0
    assert data["pass_threshold"] == 0.7
    assert data["preset"] is None
    assert data["prompt_template"] is None
    assert data["dimensions"] is None
    assert data["aggregation"] is None


@pytest.mark.asyncio
async def test_list_judges_empty(client):
    """GET /judges when empty returns empty paginated response."""
    response = await client.get("/api/v1/judges")
    assert response.status_code == 200
    data = response.json()
    assert data["items"] == []
    assert data["total"] == 0
    assert data["pages"] == 1


@pytest.mark.asyncio
async def test_list_judges_pagination(client):
    """Create 3 judges, verify pagination works correctly."""
    for i in range(3):
        await client.post("/api/v1/judges", json={"name": f"Judge {i}"})

    response = await client.get("/api/v1/judges", params={"page": 1, "page_size": 2})
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 3
    assert data["pages"] == 2
    assert len(data["items"]) == 2


@pytest.mark.asyncio
async def test_list_judges_name_filter(client):
    """Filter judges by name substring."""
    await client.post("/api/v1/judges", json={"name": "Alpha"})
    await client.post("/api/v1/judges", json={"name": "Beta"})

    response = await client.get("/api/v1/judges", params={"name": "alp"})
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 1
    assert data["items"][0]["name"] == "Alpha"


@pytest.mark.asyncio
async def test_get_judge_by_id(client):
    """Create a judge, then GET by ID returns matching fields."""
    create_response = await client.post("/api/v1/judges", json={"name": "Lookup Judge", "model": "gpt-4.1"})
    judge_id = create_response.json()["id"]

    response = await client.get(f"/api/v1/judges/{judge_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == judge_id
    assert data["name"] == "Lookup Judge"
    assert data["model"] == "gpt-4.1"


@pytest.mark.asyncio
async def test_get_judge_not_found(client):
    """GET /judges/nonexistent returns 404 with RFC 7807 body."""
    response = await client.get("/api/v1/judges/nonexistent-id")
    assert response.status_code == 404
    data = response.json()
    assert data["title"] == "Not Found"
    assert "nonexistent-id" in data["detail"]


@pytest.mark.asyncio
async def test_update_judge(client):
    """Create, then PUT with new name updates correctly."""
    create_response = await client.post("/api/v1/judges", json={"name": "Original"})
    judge_id = create_response.json()["id"]

    response = await client.put(f"/api/v1/judges/{judge_id}", json={"name": "Updated"})
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Updated"
    assert data["id"] == judge_id


@pytest.mark.asyncio
async def test_update_judge_partial(client):
    """PUT with only temperature field changes only that field."""
    create_response = await client.post("/api/v1/judges", json={"name": "Partial", "temperature": 0.0})
    judge_id = create_response.json()["id"]

    response = await client.put(f"/api/v1/judges/{judge_id}", json={"temperature": 0.9})
    assert response.status_code == 200
    data = response.json()
    assert data["temperature"] == 0.9
    assert data["name"] == "Partial"  # unchanged


@pytest.mark.asyncio
async def test_update_judge_not_found(client):
    """PUT /judges/nonexistent returns 404."""
    response = await client.put("/api/v1/judges/nonexistent-id", json={"name": "Fail"})
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_get_judge_presets(client):
    """GET /judges/presets returns presets based on configured judge providers."""
    response = await client.get("/api/v1/judges/presets")
    assert response.status_code == 200
    data = response.json()
    assert len(data) >= 1
    for preset in data:
        assert "id" in preset
        assert "name" in preset
        assert preset["id"].startswith("provider-")
