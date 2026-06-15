---
id: INFRA-001
title: The production image builds the frontend into /app/static but no process ever serves it
category: devex-infra
severity: critical
effort: S
confidence: high
breaking: false
status: open
depends_on: []
blocks: [TEST-003]
supersedes: []
superseded_by: []
conflicts_with: []
related: [INFRA-002, SEC-005]
child_of: null
affected_paths:
  - backend/app/main.py
  - Containerfile
  - nginx.conf
  - docker-compose.prod.yml
---

## Problem
The deployment chain contradicts itself: the `Containerfile` copies the built SPA into `/app/static/`; `nginx.conf` proxies `/` to the backend with the comment "The backend serves the built frontend from /app/static/"; but the FastAPI app mounts no static files at all. Following the documented production procedure yields a deployment whose UI is a 404 JSON ProblemDetail at `/`. CI's container smoke test only curls `/api/v1/health`, so the broken UI ships green.

## Evidence
- Frontend copied in: `Containerfile:34-35` (`COPY --from=build-frontend /build/dist ./static/`).
- Never mounted: `grep -rn "StaticFiles" backend/` → no hits; `backend/app/main.py` registers only routers.
- nginx comment claims otherwise: `nginx.conf:35-37`, proxying `/` to backend `:37-43`.
- Smoke test blind spot: `.github/workflows/ci.yml:95-114`.

## Impact
Production deployment is broken by construction — the single highest-severity defect in the repo's infra. Anyone evaluating the project via `docker compose -f docker-compose.prod.yml up` concludes it doesn't work.

## Root cause
The static-serving half was planned (artifacts exist on both sides of it) but the `app.mount` line was never written, and nothing in CI looks at `/`.

## Proposed fix (specification)
1. In `backend/app/main.py`, after router includes:
   ```python
   from fastapi.staticfiles import StaticFiles
   from fastapi.responses import FileResponse

   _static = Path(__file__).resolve().parents[1] / "static"
   if _static.is_dir():
       app.mount("/assets", StaticFiles(directory=_static / "assets"), name="assets")

       @app.get("/{full_path:path}", include_in_schema=False)
       async def spa(full_path: str):
           candidate = _static / full_path
           if full_path and candidate.is_file():
               return FileResponse(candidate)
           return FileResponse(_static / "index.html")
   ```
   (SPA fallback required for client-side routes like `/results/123`; the catch-all is registered last so all API/WS routes win. Guarded by `is_dir()` so dev runs without a build are unaffected.)
2. Extend the CI smoke job: `curl -sf http://localhost:8000/ | grep -qi "<!doctype html"` and one deep route (`/results`) returns HTML (TEST-003 item 4).
3. Fix the `nginx.conf` comment (now true) — no routing change needed.

## Alternatives considered
Serve static from nginx instead (copy dist into an nginx-mounted volume) — viable and slightly faster, but splits the artifact across two images and breaks the standalone single-container story (`docker run eval-studio` currently implied by the Containerfile); backend-served keeps one artifact.

## Verification
`make docker-build && docker run -p 8000:8000 eval-studio:latest` → browser at `:8000` loads the dashboard; `/results` deep link works; `docker compose -f docker-compose.prod.yml up` serves the UI via nginx at `:80`. CI smoke asserts it.

## Relationship notes
- `blocks: TEST-003` — its smoke-depth item tests the behavior introduced here.
- `related: INFRA-002` — the same first-run path also needs a schema; both must land for the production image to actually work end-to-end.
- `related: SEC-005` — serving UI and API same-origin simplifies the auth story there.
