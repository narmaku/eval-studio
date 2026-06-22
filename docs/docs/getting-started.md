# Getting Started

This guide walks you through setting up eval-studio for local development.

## Prerequisites

| Tool            | Minimum Version | Check Command       |
|-----------------|----------------|---------------------|
| Python          | 3.11+          | `python3 --version` |
| Node.js         | 22+            | `node --version`    |
| uv              | latest         | `uv --version`      |
| Docker or Podman| latest         | `docker --version`  |
| GNU Make        | 3.80+          | `make --version`    |

## Quick Start

### Option 1: Local Development (Recommended)

```bash
# Clone the repository
git clone https://github.com/narmaku/eval-studio.git
cd eval-studio

# Copy environment configuration
cp .env.example .env
# Edit .env to add your LLM API key

# Verify all tools are installed
make check-deps

# Start development servers
make dev
```

Database schema migrations run automatically on startup — no manual
`alembic` step needed. To run migrations explicitly (e.g. against a custom
`DATABASE_URL`):

```bash
cd backend && uv run alembic upgrade head
```

This starts:

- **Backend** at [http://localhost:8000](http://localhost:8000) -- FastAPI with auto-reload
- **Frontend** at [http://localhost:5173](http://localhost:5173) -- Vite dev server

### Option 2: Docker Compose

```bash
# Clone and configure
git clone https://github.com/narmaku/eval-studio.git
cd eval-studio
cp .env.example .env

# Start all services
docker compose up -d
```

To also start the LiteLLM proxy:

```bash
docker compose --profile litellm up -d
```

## Verify Installation

Once the servers are running:

1. Open [http://localhost:5173](http://localhost:5173) in your browser
2. The frontend should display the eval-studio dashboard
3. Check the API health endpoint: [http://localhost:8000/api/v1/health](http://localhost:8000/api/v1/health)

## Security Model

eval-studio is a **single-trust-domain tool**: every user or process that can
reach the API or UI is treated as fully trusted. The application makes
server-side HTTP requests to user-configured endpoints (LLM providers, RAG
backends, custom agent APIs) by design — this is how it evaluates external
systems. There is no URL allowlisting or egress filtering.

**Do not expose eval-studio beyond your trusted network.** In development the
backend binds to `127.0.0.1` by default. If you override this (e.g.
`HOST=0.0.0.0`), ensure network-level controls restrict access to authorized
users.

For shared or multi-user deployments, enable API-key authentication
(`AUTH_DISABLED=false` in `.env`) and issue keys to each user. See the
[API Reference](api-reference.md) for key management details.

## Next Steps

- Learn about the [Evaluation Modes](evaluation-modes.md) available
- Explore the [Adapters](adapters.md) architecture
- Browse the [API Reference](api-reference.md)
