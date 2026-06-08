# CI/CD Integration

eval-studio provides a dedicated **run-and-wait** endpoint
(`POST /api/v1/evaluations/run`) designed for CI/CD pipelines. It creates an
evaluation, runs it, and returns results with a pass/fail verdict -- all in a
single HTTP call.

---

## Quick Start

### 1. Deploy eval-studio

Run the eval-studio backend on a host reachable from your CI runners:

```bash
docker compose -f docker-compose.prod.yml up -d
```

### 2. Create an API key

On a fresh deployment, bootstrap mode allows creating the first key without
authentication:

```bash
EVAL_STUDIO_URL="https://eval-studio.example.com"

RAW_KEY=$(curl -s "$EVAL_STUDIO_URL/api/v1/api-keys" \
  -H "Content-Type: application/json" \
  -d '{"name": "ci-pipeline", "description": "CI/CD automation"}' \
  | jq -r '.raw_key')

echo "Save this key securely: $RAW_KEY"
```

Store the key as a secret in your CI system (e.g., GitHub Actions secret,
GitLab CI variable).

### 3. Run your first evaluation

```bash
curl -s "$EVAL_STUDIO_URL/api/v1/evaluations/run" \
  -H "Authorization: Bearer $RAW_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "smoke test",
    "mode": "qa",
    "dataset_id": "YOUR_DATASET_ID",
    "pass_threshold": 0.7
  }' | jq '{verdict, average_score, exit_code}'
```

---

## GitHub Actions

Complete workflow that runs an evaluation on every pull request and
fails the check if the score drops below the threshold.

```yaml
# .github/workflows/eval.yml
name: Evaluation Gate

on:
  pull_request:
    branches: [main]

jobs:
  evaluate:
    runs-on: ubuntu-latest
    steps:
      - name: Run evaluation
        id: eval
        env:
          EVAL_STUDIO_URL: ${{ vars.EVAL_STUDIO_URL }}
          EVAL_STUDIO_KEY: ${{ secrets.EVAL_STUDIO_KEY }}
          DATASET_ID: ${{ vars.EVAL_DATASET_ID }}
        run: |
          RESPONSE=$(curl -sf "$EVAL_STUDIO_URL/api/v1/evaluations/run" \
            -H "Authorization: Bearer $EVAL_STUDIO_KEY" \
            -H "Content-Type: application/json" \
            -d "{
              \"name\": \"PR #${{ github.event.pull_request.number }} eval\",
              \"mode\": \"qa\",
              \"dataset_id\": \"$DATASET_ID\",
              \"pass_threshold\": 0.8
            }")

          echo "$RESPONSE" | jq .

          VERDICT=$(echo "$RESPONSE" | jq -r '.verdict')
          SCORE=$(echo "$RESPONSE" | jq -r '.average_score')
          EXIT_CODE=$(echo "$RESPONSE" | jq -r '.exit_code')

          echo "score=$SCORE" >> "$GITHUB_OUTPUT"
          echo "verdict=$VERDICT" >> "$GITHUB_OUTPUT"

          exit "$EXIT_CODE"

      - name: Post result to PR
        if: always()
        uses: actions/github-script@v7
        with:
          script: |
            const score = '${{ steps.eval.outputs.score }}';
            const verdict = '${{ steps.eval.outputs.verdict }}';
            const icon = verdict === 'pass' ? ':white_check_mark:' : ':x:';
            github.rest.issues.createComment({
              issue_number: context.issue.number,
              owner: context.repo.owner,
              repo: context.repo.repo,
              body: `## Evaluation Result ${icon}\n\n| Metric | Value |\n|--------|-------|\n| Score | ${score} |\n| Verdict | ${verdict} |`
            });
```

**Setup steps:**

1. Add repository variables (`Settings > Variables`):
    - `EVAL_STUDIO_URL` -- your eval-studio base URL
    - `EVAL_DATASET_ID` -- the dataset ID to run against
2. Add repository secret (`Settings > Secrets`):
    - `EVAL_STUDIO_KEY` -- your API key (the `esk_...` value)

---

## GitLab CI

Complete pipeline configuration for GitLab CI.

```yaml
# .gitlab-ci.yml
stages:
  - evaluate

evaluation-gate:
  stage: evaluate
  image: curlimages/curl:latest
  variables:
    EVAL_STUDIO_URL: "${EVAL_STUDIO_URL}"
    DATASET_ID: "${EVAL_DATASET_ID}"
  rules:
    - if: $CI_PIPELINE_SOURCE == "merge_request_event"
  script:
    - |
      RESPONSE=$(curl -sf "$EVAL_STUDIO_URL/api/v1/evaluations/run" \
        -H "Authorization: Bearer $EVAL_STUDIO_KEY" \
        -H "Content-Type: application/json" \
        -d "{
          \"name\": \"MR !${CI_MERGE_REQUEST_IID} eval\",
          \"mode\": \"qa\",
          \"dataset_id\": \"$DATASET_ID\",
          \"pass_threshold\": 0.8
        }")

      echo "$RESPONSE" | python3 -m json.tool || echo "$RESPONSE"

      EXIT_CODE=$(echo "$RESPONSE" | grep -o '"exit_code":[0-9]*' | cut -d: -f2)
      exit "${EXIT_CODE:-1}"
```

**Setup steps:**

1. Add CI/CD variables (`Settings > CI/CD > Variables`):
    - `EVAL_STUDIO_URL` -- your eval-studio base URL (not protected)
    - `EVAL_STUDIO_KEY` -- your API key (masked, protected)
    - `EVAL_DATASET_ID` -- the dataset ID to run against

---

## Bash / curl Script

A standalone script for use in any CI system or local development.

```bash
#!/usr/bin/env bash
# eval-gate.sh -- Run an eval-studio evaluation and exit with its verdict.
#
# Usage:
#   export EVAL_STUDIO_URL="https://eval-studio.example.com"
#   export EVAL_STUDIO_KEY="esk_..."
#   ./eval-gate.sh <dataset_id> [threshold]
#
# Exit codes:
#   0 -- evaluation passed
#   1 -- evaluation failed or error

set -euo pipefail

DATASET_ID="${1:?Usage: eval-gate.sh <dataset_id> [threshold]}"
THRESHOLD="${2:-0.7}"

RESPONSE=$(curl -sf "${EVAL_STUDIO_URL}/api/v1/evaluations/run" \
  -H "Authorization: Bearer ${EVAL_STUDIO_KEY}" \
  -H "Content-Type: application/json" \
  -d "{
    \"name\": \"CLI gate check $(date -u +%Y-%m-%dT%H:%M:%SZ)\",
    \"mode\": \"qa\",
    \"dataset_id\": \"${DATASET_ID}\",
    \"pass_threshold\": ${THRESHOLD}
  }")

# Extract fields
VERDICT=$(echo "$RESPONSE" | grep -o '"verdict":"[^"]*"' | cut -d'"' -f4)
SCORE=$(echo "$RESPONSE" | grep -o '"average_score":[0-9.]*' | cut -d: -f2)
EXIT_CODE=$(echo "$RESPONSE" | grep -o '"exit_code":[0-9]*' | cut -d: -f2)

echo "Score:    ${SCORE}"
echo "Verdict:  ${VERDICT}"
echo "Exit:     ${EXIT_CODE}"

exit "${EXIT_CODE}"
```

For the simplest possible integration, use the plain text response format:

```bash
# Returns just the score and verdict -- no JSON parsing needed
RESULT=$(curl -sf "${EVAL_STUDIO_URL}/api/v1/evaluations/run" \
  -H "Authorization: Bearer ${EVAL_STUDIO_KEY}" \
  -H "Content-Type: application/json" \
  -H "Accept: text/plain" \
  -d '{
    "name": "quick check",
    "mode": "qa",
    "dataset_id": "'"${DATASET_ID}"'"
  }')

SCORE=$(echo "$RESULT" | head -1)
VERDICT=$(echo "$RESULT" | tail -1)
echo "Score: $SCORE, Verdict: $VERDICT"

# Fail if verdict is not PASS
[ "$VERDICT" = "PASS" ] || exit 1
```

---

## Async Mode with Polling

For long-running evaluations, use async mode to avoid HTTP timeouts.

```bash
# Start the evaluation (returns immediately)
ASYNC_RESPONSE=$(curl -sf "${EVAL_STUDIO_URL}/api/v1/evaluations/run?async=true" \
  -H "Authorization: Bearer ${EVAL_STUDIO_KEY}" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "nightly regression",
    "mode": "qa",
    "dataset_id": "'"${DATASET_ID}"'"
  }')

EVAL_ID=$(echo "$ASYNC_RESPONSE" | grep -o '"evaluation_id":"[^"]*"' | cut -d'"' -f4)
POLL_URL="${EVAL_STUDIO_URL}/api/v1/evaluations/${EVAL_ID}"

echo "Evaluation started: ${EVAL_ID}"

# Poll until complete
while true; do
  STATUS=$(curl -sf "$POLL_URL" \
    -H "Authorization: Bearer ${EVAL_STUDIO_KEY}" \
    | grep -o '"status":"[^"]*"' | cut -d'"' -f4)

  echo "Status: $STATUS"

  case "$STATUS" in
    completed|failed) break ;;
    *) sleep 10 ;;
  esac
done

echo "Final status: $STATUS"
[ "$STATUS" = "completed" ] || exit 1
```

---

## Configuring Pass/Fail Thresholds

The `pass_threshold` field in the run request controls when an evaluation is
considered passing. It is a float between 0.0 and 1.0, compared against the
`average_score` of all results.

| Threshold | Use case                                             |
|-----------|------------------------------------------------------|
| `0.9`     | Strict -- production release gates                   |
| `0.8`     | Standard -- PR merge checks                          |
| `0.7`     | Default -- general regression detection              |
| `0.5`     | Lenient -- early development, experimental changes   |

The verdict logic:

- `average_score >= pass_threshold` results in `verdict: "pass"`, `exit_code: 0`
- `average_score < pass_threshold` results in `verdict: "fail"`, `exit_code: 1`

---

## Interpreting Results

### Key fields in the RunResponse

| Field              | Type    | Description                                        |
|--------------------|---------|----------------------------------------------------|
| `verdict`          | string  | `"pass"` or `"fail"` based on threshold            |
| `exit_code`        | int     | `0` for pass, `1` for fail (mirrors shell exit)    |
| `average_score`    | float   | Mean score across all evaluated items              |
| `total_items`      | int     | Number of dataset items evaluated                  |
| `passed_count`     | int     | Items that passed individual scoring               |
| `failed_count`     | int     | Items that failed individual scoring               |
| `duration_seconds` | float   | Wall-clock time the evaluation took                |
| `status`           | string  | Final evaluation status (`completed`, `failed`)    |
| `error`            | string  | Error message if the evaluation failed             |

### Per-item result fields

Each entry in `results` contains:

| Field              | Type          | Description                                   |
|--------------------|---------------|-----------------------------------------------|
| `score`            | float or null | Item score (null if errored)                  |
| `passed`           | bool or null  | Whether this item passed                      |
| `actual_answer`    | string        | The model's actual response                   |
| `judge_reasoning`  | string        | The judge's explanation of the score          |
| `scores_breakdown` | object        | Per-metric breakdown (e.g., accuracy, completeness) |

---

## Timeouts

The run-and-wait endpoint enforces timeouts to prevent CI jobs from hanging:

| Setting                | Default | Max  | Environment variable    |
|------------------------|---------|------|-------------------------|
| Default timeout        | 300s    | --   | `RUN_TIMEOUT_DEFAULT`   |
| Maximum allowed        | --      | 600s | `RUN_TIMEOUT_MAX`       |

If an evaluation exceeds the timeout:

- The HTTP response has status `504 Gateway Timeout`
- The response body still contains partial results
- The `status` field reflects the evaluation's actual state at timeout

Override the timeout per request with the `timeout` query parameter:

```bash
# Allow up to 10 minutes for a large evaluation
curl -sf "${EVAL_STUDIO_URL}/api/v1/evaluations/run?timeout=600" \
  -H "Authorization: Bearer ${EVAL_STUDIO_KEY}" \
  -H "Content-Type: application/json" \
  -d '...'
```

---

## Troubleshooting

### Common issues

**`401 Unauthorized`**

- Verify the API key is correct and starts with `esk_`.
- Ensure the `Authorization` header uses the `Bearer` scheme.
- Check that the key has not been revoked (`GET /api/v1/api-keys`).

**`404 Not Found` for dataset**

- Confirm the dataset ID exists: `GET /api/v1/datasets/{id}`.
- Dataset IDs are UUIDs, not names.

**`504 Gateway Timeout`**

- Increase the `timeout` query parameter (max 600 seconds).
- Use async mode for evaluations expected to run longer than 10 minutes.
- Check that the LLM backend (LiteLLM) is responding.

**`422 Validation Error`**

- For arena mode: ensure `config.contestants` has at least 2 entries.
- Check that `pass_threshold` is between 0.0 and 1.0.
- Verify all required fields are present in the request body.

**`409 Conflict`**

- Cannot delete a running evaluation -- wait for it to complete or fail.
- Cannot revoke the last active API key.

**Connection refused / timeout**

- Verify the eval-studio backend is running and reachable from CI runners.
- Check firewall rules between CI infrastructure and the eval-studio host.
- For Docker deployments, ensure port 8000 is published.

### Debugging tips

1. **Test connectivity first:**
   ```bash
   curl -sf "${EVAL_STUDIO_URL}/api/v1/health" | jq .
   ```

2. **Verify authentication:**
   ```bash
   curl -sf "${EVAL_STUDIO_URL}/api/v1/api-keys" \
     -H "Authorization: Bearer ${EVAL_STUDIO_KEY}" | jq .total
   ```

3. **Check available datasets:**
   ```bash
   curl -sf "${EVAL_STUDIO_URL}/api/v1/datasets" \
     -H "Authorization: Bearer ${EVAL_STUDIO_KEY}" | jq '.items[].name'
   ```

4. **Run with verbose curl output:**
   ```bash
   curl -v "${EVAL_STUDIO_URL}/api/v1/evaluations/run" \
     -H "Authorization: Bearer ${EVAL_STUDIO_KEY}" \
     -H "Content-Type: application/json" \
     -d '...'
   ```
