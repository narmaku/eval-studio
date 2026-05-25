# Containerfile -- Multi-stage production build for eval-studio

# Stage 1: Build frontend
FROM node:22-slim AS build-frontend

WORKDIR /build

COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci --silent

COPY frontend/ .
RUN npm run build

# Stage 2: Python runtime
FROM python:3.11-slim AS runtime

# Install system dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends curl && \
    rm -rf /var/lib/apt/lists/*

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

WORKDIR /app

# Install Python dependencies (cached layer)
COPY backend/pyproject.toml backend/uv.lock* ./
RUN uv sync --no-dev --frozen

# Copy backend source
COPY backend/ .

# Copy frontend build output
COPY --from=build-frontend /build/dist ./static/

# Create data directory for SQLite
RUN mkdir -p /app/data

# Run as non-root user (OpenShift compatible)
RUN chown -R 1001:0 /app && chmod -R g=u /app
USER 1001

EXPOSE 8000

CMD ["uv", "run", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
