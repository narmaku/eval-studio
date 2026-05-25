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
git clone https://github.com/eval-studio/eval-studio.git
cd eval-studio

# Copy environment configuration
cp .env.example .env
# Edit .env to add your LLM API key

# Verify all tools are installed
make check-deps

# Start development servers
make dev
```

This starts:

- **Backend** at [http://localhost:8000](http://localhost:8000) -- FastAPI with auto-reload
- **Frontend** at [http://localhost:5173](http://localhost:5173) -- Vite dev server

### Option 2: Docker Compose

```bash
# Clone and configure
git clone https://github.com/eval-studio/eval-studio.git
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

## Next Steps

- Learn about the [Evaluation Modes](evaluation-modes.md) available
- Explore the [Adapters](adapters.md) architecture
- Set up [Environments](environments.md) for agent evaluation
- Browse the [API Reference](api-reference.md)
