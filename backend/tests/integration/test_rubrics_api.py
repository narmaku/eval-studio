"""Integration tests for the Rubrics CRUD API."""

import textwrap
from unittest.mock import patch

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


# --- Import endpoint tests ---


VALID_YAML = textwrap.dedent("""\
    rubric:
      name: "Imported Rubric"
      description: "Imported from YAML"
      dimensions:
        - name: accuracy
          weight: 0.6
          description: "Factual accuracy"
        - name: completeness
          weight: 0.4
          description: "Answer completeness"
      pass_threshold: 0.8
      aggregation: weighted_average
""")


@pytest.mark.asyncio
async def test_import_rubric_success(client):
    """POST /rubrics/import creates a rubric from valid YAML."""
    response = await client.post("/api/v1/rubrics/import", json={"yaml_content": VALID_YAML})
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Imported Rubric"
    assert data["description"] == "Imported from YAML"
    assert len(data["dimensions"]) == 2
    assert data["dimensions"][0]["name"] == "accuracy"
    assert data["pass_threshold"] == 0.8
    assert data["id"] is not None


@pytest.mark.asyncio
async def test_import_rubric_flat_format(client):
    """POST /rubrics/import accepts flat YAML format."""
    yaml_content = textwrap.dedent("""\
        name: "Flat Import"
        dimensions:
          - name: quality
            weight: 1.0
            description: "Overall quality"
    """)
    response = await client.post("/api/v1/rubrics/import", json={"yaml_content": yaml_content})
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Flat Import"


@pytest.mark.asyncio
async def test_import_rubric_invalid_yaml(client):
    """POST /rubrics/import returns 400 for invalid YAML."""
    response = await client.post("/api/v1/rubrics/import", json={"yaml_content": "key: [unclosed"})
    assert response.status_code == 400
    data = response.json()
    assert "Invalid YAML" in data["detail"]


@pytest.mark.asyncio
async def test_import_rubric_no_dimensions(client):
    """POST /rubrics/import returns 400 when no dimensions in YAML."""
    response = await client.post("/api/v1/rubrics/import", json={"yaml_content": "name: No Dims"})
    assert response.status_code == 400
    assert "No dimensions" in response.json()["detail"]


@pytest.mark.asyncio
async def test_import_rubric_empty_body(client):
    """POST /rubrics/import returns 422 for empty yaml_content."""
    response = await client.post("/api/v1/rubrics/import", json={"yaml_content": ""})
    assert response.status_code == 422


# --- Generate endpoint tests ---


@pytest.mark.asyncio
async def test_generate_rubric_success(client):
    """POST /rubrics/generate creates a rubric via LLM."""
    from rubric_kit import Criterion, Dimension, GenerationResult, Rubric

    mock_rubric = Rubric(
        dimensions=[
            Dimension(name="quality", description="Quality assessment", grading_type="score", scores={1: "Bad", 5: "Good"}),
        ],
        criteria=[
            Criterion(name="q1", weight=3, dimension="quality", criterion="Is it good?"),
        ],
    )
    mock_result = GenerationResult(
        rubric=mock_rubric, model="test-model", input_type="qna", input_source="<in-memory>"
    )

    with patch("app.services.rubric_service.rubric_kit_generate", return_value=mock_result):
        response = await client.post(
            "/api/v1/rubrics/generate",
            json={"description": "Evaluate Q&A accuracy", "provider_id": "__test__"},
        )

    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Generated Rubric"
    assert data["description"] == "Evaluate Q&A accuracy"
    assert len(data["dimensions"]) == 1
    assert data["id"] is not None


@pytest.mark.asyncio
async def test_generate_rubric_unknown_provider(client):
    """POST /rubrics/generate returns 400 for unknown provider."""
    response = await client.post(
        "/api/v1/rubrics/generate",
        json={"description": "Test", "provider_id": "nonexistent-provider"},
    )
    assert response.status_code == 400
    assert "Provider" in response.json()["detail"]


@pytest.mark.asyncio
async def test_generate_rubric_empty_description(client):
    """POST /rubrics/generate returns 422 for empty description."""
    response = await client.post(
        "/api/v1/rubrics/generate",
        json={"description": "", "provider_id": "__test__"},
    )
    assert response.status_code == 422


# --- Refine endpoint tests ---


@pytest.mark.asyncio
async def test_refine_rubric_success(client):
    """POST /rubrics/{id}/refine refines an existing rubric."""
    # First create a rubric
    create_resp = await client.post("/api/v1/rubrics", json=RUBRIC_PAYLOAD)
    rubric_id = create_resp.json()["id"]

    from rubric_kit import Criterion, Dimension, RefinementResult, Rubric

    mock_rubric = Rubric(
        dimensions=[
            Dimension(name="accuracy", description="Factual accuracy", grading_type="score", scores={1: "1", 5: "5"}),
            Dimension(name="clarity", description="Response clarity", grading_type="score", scores={1: "1", 5: "5"}),
        ],
        criteria=[
            Criterion(name="c1", weight=2, dimension="accuracy", criterion="Accurate?"),
            Criterion(name="c2", weight=1, dimension="clarity", criterion="Clear?"),
        ],
    )
    mock_result = RefinementResult(
        rubric=mock_rubric, original_rubric=mock_rubric, model="test-model", had_feedback=True
    )

    with patch("app.services.rubric_service.rubric_kit_refine", return_value=mock_result):
        response = await client.post(
            f"/api/v1/rubrics/{rubric_id}/refine",
            json={"feedback": "Add a clarity dimension", "provider_id": "__test__"},
        )

    assert response.status_code == 200
    data = response.json()
    assert data["id"] == rubric_id
    assert len(data["dimensions"]) == 2
    # Should keep original name
    assert data["name"] == "Test Rubric"


@pytest.mark.asyncio
async def test_refine_rubric_not_found(client):
    """POST /rubrics/nonexistent/refine returns 404."""
    response = await client.post(
        "/api/v1/rubrics/nonexistent-id/refine",
        json={"feedback": "test", "provider_id": "__test__"},
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_refine_rubric_unknown_provider(client):
    """POST /rubrics/{id}/refine returns 400 for unknown provider."""
    create_resp = await client.post("/api/v1/rubrics", json=RUBRIC_PAYLOAD)
    rubric_id = create_resp.json()["id"]

    response = await client.post(
        f"/api/v1/rubrics/{rubric_id}/refine",
        json={"feedback": "test", "provider_id": "nonexistent-provider"},
    )
    assert response.status_code == 400
