# API Reference

eval-studio exposes a REST API under `/api/v1/` for all operations. The API
follows RESTful conventions with JSON request/response bodies, Pydantic schema
validation, and RFC 7807 Problem Details for error responses.

When the backend is running, interactive API documentation is available at:

- **Swagger UI**: [http://localhost:8000/docs](http://localhost:8000/docs)
- **ReDoc**: [http://localhost:8000/redoc](http://localhost:8000/redoc)

---

## Authentication

eval-studio supports **API key authentication** via Bearer tokens.
**Authentication is disabled by default** (`AUTH_DISABLED=true`) — the
application is designed as a single-trust-domain local tool (see
[Security Model](getting-started.md#security-model)). When enabled, all
REST and WebSocket endpoints except `/api/v1/health` require a valid API key.

### Creating your first API key (bootstrap mode)

When no API keys exist yet, the `POST /api/v1/api-keys` endpoint skips
authentication so you can create the first key without a chicken-and-egg
problem. Once at least one active key exists, all subsequent key creation
requests require authentication.

```bash
# Bootstrap: create the first API key (no auth needed)
curl -s http://localhost:8000/api/v1/api-keys \
  -H "Content-Type: application/json" \
  -d '{"name": "my-first-key"}' | jq .
```

The response includes a `raw_key` field -- **save it immediately**. The raw
key is only returned once and cannot be retrieved again.

### Using API keys

Pass your key in the `Authorization` header with the `Bearer` scheme:

```bash
curl http://localhost:8000/api/v1/evaluations \
  -H "Authorization: Bearer esk_abc123..."
```

All keys use the `esk_` prefix (eval-studio key).

### Disabling authentication for development

Set the `AUTH_DISABLED=true` environment variable to skip authentication
on all endpoints. This is intended for local development only.

```bash
AUTH_DISABLED=true uv run uvicorn app.main:app --reload
```

!!! warning
    Never disable authentication in production. The `AUTH_DISABLED` flag
    bypasses all security checks.

---

## API Key Management

### Create API key

`POST /api/v1/api-keys`

Create a new API key. In bootstrap mode (no active keys exist), authentication
is not required. Otherwise, a valid Bearer token must be provided.

**Request body:**

| Field         | Type              | Required | Description                              |
|---------------|-------------------|----------|------------------------------------------|
| `name`        | `string`          | Yes      | Human-readable name (1--255 characters)  |
| `description` | `string` or null  | No       | Optional description of the key's purpose |

```bash
curl -s http://localhost:8000/api/v1/api-keys \
  -H "Authorization: Bearer esk_abc123..." \
  -H "Content-Type: application/json" \
  -d '{"name": "ci-pipeline", "description": "Used by GitHub Actions"}' | jq .
```

**Response** (`201 Created`):

```json
{
  "id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "name": "ci-pipeline",
  "key_prefix": "esk_abc123...",
  "is_active": true,
  "description": "Used by GitHub Actions",
  "created_at": "2025-01-15T10:30:00Z",
  "last_used_at": null,
  "raw_key": "esk_abc123def456ghi789jkl012mno345pqr678stu"
}
```

!!! warning
    The `raw_key` field is only included in the creation response. Store it
    securely -- it cannot be retrieved later.

### List API keys

`GET /api/v1/api-keys`

List all API keys with pagination. The raw key and hash are never exposed.

**Query parameters:**

| Parameter   | Type  | Default | Description                          |
|-------------|-------|---------|--------------------------------------|
| `page`      | `int` | `1`     | Page number (1-based)                |
| `page_size` | `int` | `20`    | Number of items per page             |

```bash
curl -s http://localhost:8000/api/v1/api-keys \
  -H "Authorization: Bearer esk_abc123..." | jq .
```

**Response** (`200 OK`):

```json
{
  "items": [
    {
      "id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
      "name": "ci-pipeline",
      "key_prefix": "esk_abc123...",
      "is_active": true,
      "description": "Used by GitHub Actions",
      "created_at": "2025-01-15T10:30:00Z",
      "last_used_at": "2025-01-16T08:00:00Z"
    }
  ],
  "total": 1,
  "page": 1,
  "page_size": 20,
  "pages": 1
}
```

### Revoke API key

`DELETE /api/v1/api-keys/{id}`

Deactivate an API key. Revoked keys can no longer be used for authentication.
The last active key cannot be revoked to prevent lockout.

```bash
curl -s -X DELETE http://localhost:8000/api/v1/api-keys/a1b2c3d4-e5f6-7890-abcd-ef1234567890 \
  -H "Authorization: Bearer esk_abc123..."
```

**Response:** `204 No Content`

**Error responses:**

- `404` -- API key not found.
- `409` -- Cannot revoke the last active API key.

---

## Evaluations

### Create evaluation

`POST /api/v1/evaluations`

Create a new evaluation without running it. The evaluation is created in
`pending` status and can be started later with the run endpoint.

**Request body:**

| Field             | Type              | Required | Description                                          |
|-------------------|-------------------|----------|------------------------------------------------------|
| `name`            | `string`          | Yes      | Human-readable evaluation name                       |
| `mode`            | `string`          | Yes      | Evaluation mode: `qa`, `rag`, `agent`, or `arena`   |
| `dataset_id`      | `string` or null  | No       | ID of the dataset to evaluate against                |
| `environment_id`  | `string` or null  | No       | ID of the environment to use                         |
| `judge_config_id` | `string` or null  | No       | ID of the judge configuration                        |
| `config`          | `object`          | No       | Mode-specific configuration (defaults to `{}`)       |

```bash
curl -s http://localhost:8000/api/v1/evaluations \
  -H "Authorization: Bearer esk_abc123..." \
  -H "Content-Type: application/json" \
  -d '{
    "name": "RHEL 9 Q&A baseline",
    "mode": "qa",
    "dataset_id": "ds-001",
    "judge_config_id": "judge-001",
    "config": {}
  }' | jq .
```

**Response** (`201 Created`):

```json
{
  "id": "eval-abc123",
  "name": "RHEL 9 Q&A baseline",
  "mode": "qa",
  "status": "pending",
  "error": null,
  "dataset_id": "ds-001",
  "environment_id": null,
  "judge_config_id": "judge-001",
  "config": {},
  "result_count": null,
  "created_at": "2025-01-15T10:30:00Z",
  "updated_at": "2025-01-15T10:30:00Z"
}
```

!!! note "Arena mode"
    Arena evaluations require at least 2 contestants in `config.contestants`.
    The request will be rejected with a `422` error if fewer are provided.

### List evaluations

`GET /api/v1/evaluations`

List evaluations with pagination and optional filtering by mode or status.

**Query parameters:**

| Parameter   | Type              | Default | Description                                          |
|-------------|-------------------|---------|------------------------------------------------------|
| `page`      | `int`             | `1`     | Page number (1-based)                                |
| `page_size` | `int`             | `20`    | Number of items per page                             |
| `mode`      | `string` or null  | null    | Filter by mode: `qa`, `rag`, `agent`, `arena`       |
| `status`    | `string` or null  | null    | Filter by status: `pending`, `running`, `completed`, `failed`, `cancelled` |

```bash
# List all completed Q&A evaluations
curl -s "http://localhost:8000/api/v1/evaluations?mode=qa&status=completed" \
  -H "Authorization: Bearer esk_abc123..." | jq .
```

**Response** (`200 OK`):

```json
{
  "items": [
    {
      "id": "eval-abc123",
      "name": "RHEL 9 Q&A baseline",
      "mode": "qa",
      "status": "completed",
      "error": null,
      "dataset_id": "ds-001",
      "environment_id": null,
      "judge_config_id": "judge-001",
      "config": {},
      "result_count": null,
      "created_at": "2025-01-15T10:30:00Z",
      "updated_at": "2025-01-15T10:35:00Z"
    }
  ],
  "total": 1,
  "page": 1,
  "page_size": 20,
  "pages": 1
}
```

### Get evaluation

`GET /api/v1/evaluations/{id}`

Retrieve a single evaluation by ID, including a count of associated results.

```bash
curl -s http://localhost:8000/api/v1/evaluations/eval-abc123 \
  -H "Authorization: Bearer esk_abc123..." | jq .
```

**Response** (`200 OK`):

```json
{
  "id": "eval-abc123",
  "name": "RHEL 9 Q&A baseline",
  "mode": "qa",
  "status": "completed",
  "error": null,
  "dataset_id": "ds-001",
  "environment_id": null,
  "judge_config_id": "judge-001",
  "config": {},
  "result_count": 50,
  "created_at": "2025-01-15T10:30:00Z",
  "updated_at": "2025-01-15T10:35:00Z"
}
```

### Delete evaluation

`DELETE /api/v1/evaluations/{id}`

Delete an evaluation and all its associated results. Running evaluations cannot
be deleted.

```bash
curl -s -X DELETE http://localhost:8000/api/v1/evaluations/eval-abc123 \
  -H "Authorization: Bearer esk_abc123..."
```

**Response:** `204 No Content`

**Error responses:**

- `404` -- Evaluation not found.
- `409` -- Cannot delete a running evaluation.

### Run evaluation

`POST /api/v1/evaluations/{id}/run`

Trigger an evaluation run as a background task. Only evaluations in `pending`
or `failed` status can be started. Supported modes: `qa`, `rag`, `arena`.

```bash
curl -s -X POST http://localhost:8000/api/v1/evaluations/eval-abc123/run \
  -H "Authorization: Bearer esk_abc123..." | jq .
```

**Response** (`200 OK`): Returns the evaluation with its updated status.

**Error responses:**

- `404` -- Evaluation not found.
- `409` -- Evaluation is not in `pending` or `failed` status.
- `501` -- Evaluation mode not yet implemented.

### Re-run evaluation

`POST /api/v1/evaluations/{id}/rerun`

Re-run a completed or failed evaluation. This clears all existing results
and starts a fresh run as a background task. Running evaluations cannot be
re-run.

```bash
curl -s -X POST http://localhost:8000/api/v1/evaluations/eval-abc123/rerun \
  -H "Authorization: Bearer esk_abc123..." | jq .
```

**Response** (`200 OK`): Returns the evaluation with status reset to `pending`.

**Error responses:**

- `404` -- Evaluation not found.
- `409` -- Evaluation is currently running.
- `501` -- Evaluation mode not yet implemented.

---

## Run-and-Wait (CI/CD endpoint)

`POST /api/v1/evaluations/run`

Create an evaluation and run it in a single request. This is the primary
endpoint for CI/CD integration -- it creates the evaluation, executes it,
and returns the aggregated results with a pass/fail verdict.

### Request body

| Field             | Type              | Required | Default | Description                                   |
|-------------------|-------------------|----------|---------|-----------------------------------------------|
| `name`            | `string`          | Yes      |         | Human-readable evaluation name                |
| `mode`            | `string`          | Yes      |         | Evaluation mode: `qa`, `rag`, `agent`, `arena`|
| `dataset_id`      | `string`          | Yes      |         | ID of the dataset to evaluate against         |
| `judge_config_id` | `string` or null  | No       | null    | ID of the judge configuration                 |
| `config`          | `object`          | No       | `{}`    | Mode-specific configuration                   |
| `environment_id`  | `string` or null  | No       | null    | ID of the environment to use                  |
| `pass_threshold`  | `float`           | No       | `0.7`   | Score threshold for pass/fail (0.0--1.0)      |

### Query parameters

| Parameter | Type   | Default | Description                                         |
|-----------|--------|---------|-----------------------------------------------------|
| `async`   | `bool` | `false` | If true, return immediately with a 202 and poll URL |
| `timeout` | `int`  | `300`   | Maximum seconds to wait (must be <= 600)            |

### Synchronous mode (default)

Blocks until the evaluation completes or times out, then returns full results.

```bash
curl -s http://localhost:8000/api/v1/evaluations/run \
  -H "Authorization: Bearer esk_abc123..." \
  -H "Content-Type: application/json" \
  -d '{
    "name": "PR check - RHEL Q&A",
    "mode": "qa",
    "dataset_id": "ds-001",
    "pass_threshold": 0.8,
    "config": {}
  }' | jq .
```

**Response** (`200 OK`):

```json
{
  "evaluation_id": "eval-xyz789",
  "status": "completed",
  "mode": "qa",
  "total_items": 50,
  "passed_count": 42,
  "failed_count": 8,
  "average_score": 0.84,
  "verdict": "pass",
  "exit_code": 0,
  "pass_threshold": 0.8,
  "duration_seconds": 45.2,
  "results": [
    {
      "id": "res-001",
      "evaluation_id": "eval-xyz789",
      "dataset_item_id": "item-001",
      "session_id": null,
      "contestant_model": null,
      "score": 0.9,
      "passed": true,
      "actual_answer": "RHEL 9 uses systemd as its init system...",
      "judge_reasoning": "Answer correctly identifies systemd...",
      "scores_breakdown": {"accuracy": 0.95, "completeness": 0.85},
      "retrieved_chunks": null,
      "created_at": "2025-01-15T10:31:00Z"
    }
  ],
  "error": null
}
```

The `verdict` is `"pass"` when `average_score >= pass_threshold`, otherwise
`"fail"`. The `exit_code` mirrors this: `0` for pass, `1` for fail.

**Timeout response** (`504 Gateway Timeout`): If the evaluation exceeds the
timeout, the same response shape is returned with a `504` status code. The
results reflect whatever was completed before the timeout.

### Async mode

When `async=true`, the evaluation is launched as a background task and the
endpoint returns immediately.

```bash
curl -s "http://localhost:8000/api/v1/evaluations/run?async=true" \
  -H "Authorization: Bearer esk_abc123..." \
  -H "Content-Type: application/json" \
  -d '{
    "name": "nightly regression",
    "mode": "qa",
    "dataset_id": "ds-001"
  }' | jq .
```

**Response** (`202 Accepted`):

```json
{
  "evaluation_id": "eval-xyz789",
  "status": "running",
  "poll_url": "/api/v1/evaluations/eval-xyz789"
}
```

Poll `GET /api/v1/evaluations/{id}` until `status` changes to `completed`
or `failed`.

### Plain text response

When the `Accept` header is `text/plain`, the response body is a two-line
string for easy parsing in shell scripts:

```bash
curl -s http://localhost:8000/api/v1/evaluations/run \
  -H "Authorization: Bearer esk_abc123..." \
  -H "Content-Type: application/json" \
  -H "Accept: text/plain" \
  -d '{
    "name": "quick check",
    "mode": "qa",
    "dataset_id": "ds-001"
  }'
```

**Response:**

```
0.84
PASS
```

The first line is the average score, the second line is the verdict
(`PASS` or `FAIL`).

---

## Datasets

### Create dataset

`POST /api/v1/datasets`

Create a new dataset with optional inline items.

**Request body:**

| Field         | Type                 | Required | Default       | Description                      |
|---------------|----------------------|----------|---------------|----------------------------------|
| `name`        | `string`             | Yes      |               | Dataset name (1--255 characters) |
| `description` | `string` or null     | No       | null          | Description of the dataset       |
| `format`      | `string`             | No       | `"qa_pairs"`  | Format identifier                |
| `version`     | `string`             | No       | `"1.0"`       | Version string                   |
| `tags`        | `array` of `string`  | No       | `[]`          | Tags for categorization          |
| `items`       | `array` of objects   | No       | `[]`          | Inline dataset items             |

Each item in `items` has:

| Field             | Type             | Required | Description          |
|-------------------|------------------|----------|----------------------|
| `question`        | `string`         | Yes      | The question text    |
| `expected_answer` | `string` or null | No       | Expected answer text |
| `metadata`        | `object` or null | No       | Arbitrary metadata   |

```bash
curl -s http://localhost:8000/api/v1/datasets \
  -H "Authorization: Bearer esk_abc123..." \
  -H "Content-Type: application/json" \
  -d '{
    "name": "RHEL 9 basics",
    "description": "Basic RHEL 9 knowledge questions",
    "tags": ["rhel9", "basics"],
    "items": [
      {
        "question": "What init system does RHEL 9 use?",
        "expected_answer": "systemd"
      },
      {
        "question": "What package manager does RHEL 9 use?",
        "expected_answer": "dnf"
      }
    ]
  }' | jq .
```

**Response** (`201 Created`):

```json
{
  "id": "ds-abc123",
  "name": "RHEL 9 basics",
  "description": "Basic RHEL 9 knowledge questions",
  "format": "qa_pairs",
  "version": "1.0",
  "tags": ["rhel9", "basics"],
  "source_type": "upload",
  "item_count": 2,
  "created_at": "2025-01-15T10:30:00Z",
  "updated_at": "2025-01-15T10:30:00Z",
  "items": [
    {
      "id": "item-001",
      "question": "What init system does RHEL 9 use?",
      "expected_answer": "systemd",
      "metadata": null,
      "order_index": 0
    },
    {
      "id": "item-002",
      "question": "What package manager does RHEL 9 use?",
      "expected_answer": "dnf",
      "metadata": null,
      "order_index": 1
    }
  ]
}
```

### List datasets

`GET /api/v1/datasets`

List datasets with pagination and optional name filter (case-insensitive
substring match).

**Query parameters:**

| Parameter   | Type             | Default | Description                        |
|-------------|------------------|---------|------------------------------------|
| `page`      | `int`            | `1`     | Page number (1-based)              |
| `page_size` | `int`            | `20`    | Number of items per page           |
| `name`      | `string` or null | null    | Filter by name (substring, case-insensitive) |

```bash
curl -s "http://localhost:8000/api/v1/datasets?name=rhel" \
  -H "Authorization: Bearer esk_abc123..." | jq .
```

**Response** (`200 OK`): Paginated list of datasets (without inline items).

### Get dataset

`GET /api/v1/datasets/{id}`

Retrieve a dataset by ID, including all its items sorted by `order_index`.

```bash
curl -s http://localhost:8000/api/v1/datasets/ds-abc123 \
  -H "Authorization: Bearer esk_abc123..." | jq .
```

**Response** (`200 OK`): Full dataset with items (same shape as create response).

### Update dataset

`PUT /api/v1/datasets/{id}`

Update dataset metadata. This does not modify the dataset items.

**Request body** (all fields optional):

| Field         | Type                | Description               |
|---------------|---------------------|---------------------------|
| `name`        | `string` or null    | Updated name              |
| `description` | `string` or null    | Updated description       |
| `tags`        | `array` or null     | Updated tags              |
| `version`     | `string` or null    | Updated version           |

```bash
curl -s -X PUT http://localhost:8000/api/v1/datasets/ds-abc123 \
  -H "Authorization: Bearer esk_abc123..." \
  -H "Content-Type: application/json" \
  -d '{"tags": ["rhel9", "basics", "v2"]}' | jq .
```

**Response** (`200 OK`): Updated dataset (without items).

### Delete dataset

`DELETE /api/v1/datasets/{id}`

Delete a dataset and all its items.

```bash
curl -s -X DELETE http://localhost:8000/api/v1/datasets/ds-abc123 \
  -H "Authorization: Bearer esk_abc123..."
```

**Response:** `204 No Content`

---

## Results

### List results

`GET /api/v1/results`

List evaluation results with pagination and optional evaluation filter.

**Query parameters:**

| Parameter       | Type             | Default | Description                          |
|-----------------|------------------|---------|--------------------------------------|
| `page`          | `int`            | `1`     | Page number (1-based)                |
| `page_size`     | `int`            | `20`    | Number of items per page             |
| `evaluation_id` | `string` or null | null    | Filter results by evaluation ID      |

```bash
curl -s "http://localhost:8000/api/v1/results?evaluation_id=eval-abc123" \
  -H "Authorization: Bearer esk_abc123..." | jq .
```

**Response** (`200 OK`):

```json
{
  "items": [
    {
      "id": "res-001",
      "evaluation_id": "eval-abc123",
      "dataset_item_id": "item-001",
      "session_id": null,
      "contestant_model": null,
      "score": 0.9,
      "passed": true,
      "actual_answer": "RHEL 9 uses systemd...",
      "judge_reasoning": "Answer correctly identifies...",
      "scores_breakdown": {"accuracy": 0.95, "completeness": 0.85},
      "retrieved_chunks": null,
      "created_at": "2025-01-15T10:31:00Z"
    }
  ],
  "total": 50,
  "page": 1,
  "page_size": 20,
  "pages": 3
}
```

### Get result

`GET /api/v1/results/{id}`

Retrieve a single result by ID.

```bash
curl -s http://localhost:8000/api/v1/results/res-001 \
  -H "Authorization: Bearer esk_abc123..." | jq .
```

**Response** (`200 OK`): Single result object (same shape as items in list).

### Compare evaluations

`GET /api/v1/results/compare`

Compare results across multiple evaluations. All evaluations must share the
same mode and dataset. Returns per-evaluation aggregate statistics and
per-item aligned comparisons.

**Query parameters:**

| Parameter                 | Type             | Required | Description                              |
|---------------------------|------------------|----------|------------------------------------------|
| `evaluation_id`           | `array[string]`  | Yes      | Two or more evaluation IDs (repeat param)|
| `reference_evaluation_id` | `string` or null | No       | Mark one evaluation as the reference     |

```bash
curl -s "http://localhost:8000/api/v1/results/compare?evaluation_id=eval-001&evaluation_id=eval-002" \
  -H "Authorization: Bearer esk_abc123..." | jq .
```

**Response** (`200 OK`):

```json
{
  "evaluations": [
    {
      "evaluation_id": "eval-001",
      "evaluation_name": "Baseline v1",
      "total_items": 50,
      "passed_count": 40,
      "failed_count": 10,
      "average_score": 0.80,
      "min_score": 0.2,
      "max_score": 1.0,
      "results": []
    },
    {
      "evaluation_id": "eval-002",
      "evaluation_name": "Improved v2",
      "total_items": 50,
      "passed_count": 45,
      "failed_count": 5,
      "average_score": 0.90,
      "min_score": 0.5,
      "max_score": 1.0,
      "results": []
    }
  ],
  "item_comparisons": [
    {
      "dataset_item_id": "item-001",
      "results": []
    }
  ],
  "reference_evaluation_id": null
}
```

**Error responses:**

- `422` -- Fewer than 2 evaluation IDs, mismatched modes, or mismatched datasets.
- `404` -- One or more evaluations not found.

### Arena leaderboard

`GET /api/v1/results/arena/{evaluation_id}`

Get the arena leaderboard for a specific evaluation. Returns contestants
ranked by average score.

```bash
curl -s http://localhost:8000/api/v1/results/arena/eval-arena-001 \
  -H "Authorization: Bearer esk_abc123..." | jq .
```

**Response** (`200 OK`):

```json
{
  "evaluation_id": "eval-arena-001",
  "evaluation_name": "Model Comparison Q1",
  "contestants": [
    {
      "contestant_model": "gpt-4",
      "total_items": 100,
      "passed_count": 92,
      "failed_count": 6,
      "errored_count": 2,
      "average_score": 0.92,
      "min_score": 0.3,
      "max_score": 1.0,
      "average_breakdown": {"accuracy": 0.94, "completeness": 0.90}
    },
    {
      "contestant_model": "claude-3-opus",
      "total_items": 100,
      "passed_count": 88,
      "failed_count": 10,
      "errored_count": 2,
      "average_score": 0.88,
      "min_score": 0.2,
      "max_score": 1.0,
      "average_breakdown": {"accuracy": 0.90, "completeness": 0.86}
    }
  ]
}
```

**Error responses:**

- `404` -- Evaluation not found.
- `422` -- Evaluation is not in `arena` mode.

---

## Health

### Health check

`GET /api/v1/health`

Returns the application health status and version. This endpoint does **not**
require authentication.

```bash
curl -s http://localhost:8000/api/v1/health | jq .
```

**Response** (`200 OK`):

```json
{
  "status": "healthy",
  "version": "0.1.0"
}
```

---

## Common Patterns

### Pagination

All list endpoints return a paginated response envelope:

```json
{
  "items": [],
  "total": 100,
  "page": 1,
  "page_size": 20,
  "pages": 5
}
```

Use `page` and `page_size` query parameters to navigate through results.
Pages are 1-based.

### Error responses

All errors follow the [RFC 7807 Problem Details](https://tools.ietf.org/html/rfc7807)
format:

```json
{
  "type": "about:blank",
  "title": "Not Found",
  "status": 404,
  "detail": "Evaluation with id 'eval-missing' not found",
  "instance": "/api/v1/evaluations/eval-missing"
}
```

Standard error codes used by the API:

| Status | Title              | When                                                  |
|--------|--------------------|-------------------------------------------------------|
| `401`  | Unauthorized       | Missing or invalid API key                            |
| `404`  | Not Found          | Resource does not exist                               |
| `409`  | Conflict           | Operation conflicts with current state (e.g., deleting a running evaluation) |
| `422`  | Validation Error   | Request data fails business-level validation          |
| `501`  | Not Implemented    | Feature or evaluation mode not yet supported          |
| `504`  | Gateway Timeout    | Evaluation exceeded the timeout in run-and-wait mode  |

### Content negotiation

The run-and-wait endpoint (`POST /api/v1/evaluations/run`) supports content
negotiation:

| `Accept` header      | Response format                                    |
|----------------------|----------------------------------------------------|
| `application/json`   | Full JSON response with all evaluation results     |
| `text/plain`         | Two-line plain text: `{score}\n{VERDICT}`          |

If no `Accept` header is provided, `application/json` is used by default.
