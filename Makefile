.DEFAULT_GOAL := help
.PHONY: help check-deps dev test test-backend test-frontend lint format build clean docker-build docker-up docker-down docs-serve docs-build

help: ## Show available targets
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

check-deps: ## Validate required development tools are installed
	@echo "Checking dependencies..."
	@command -v uv >/dev/null 2>&1 || { echo "ERROR: 'uv' is not installed. Install it: https://docs.astral.sh/uv/getting-started/installation/"; exit 1; }
	@command -v node >/dev/null 2>&1 || { echo "ERROR: 'node' is not installed. Install Node.js 22+: https://nodejs.org/"; exit 1; }
	@command -v npm >/dev/null 2>&1 || { echo "ERROR: 'npm' is not installed. It should come with Node.js."; exit 1; }
	@command -v docker >/dev/null 2>&1 || command -v podman >/dev/null 2>&1 || { echo "ERROR: Neither 'docker' nor 'podman' is installed."; exit 1; }
	@echo "All dependencies found."

dev: check-deps ## Start backend + frontend dev servers
	@./dev.sh

test: test-backend test-frontend ## Run all tests

test-backend: ## Run backend tests (pytest)
	cd backend && uv run pytest -v

test-frontend: ## Run frontend tests (vitest)
	cd frontend && npm test -- --run

lint: ## Run all linters (ruff + eslint)
	cd backend && uv run ruff check .
	cd backend && uv run ruff format --check .
	cd frontend && npm run lint

format: ## Run all formatters (ruff + prettier)
	cd backend && uv run ruff format .
	cd backend && uv run ruff check --fix .
	cd frontend && npm run format

build: ## Production build (backend deps + frontend bundle)
	cd backend && uv sync --no-dev
	cd frontend && npm ci && npm run build

clean: ## Clean build artifacts and caches
	rm -rf frontend/dist frontend/node_modules/.cache
	rm -rf backend/.pytest_cache backend/__pycache__
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .pytest_cache -exec rm -rf {} + 2>/dev/null || true
	rm -rf site/

docker-build: ## Build production container image
	docker build -f Containerfile -t eval-studio:latest .

docker-up: ## Start development environment (docker compose)
	docker compose up -d

docker-down: ## Stop development environment (docker compose)
	docker compose down

docs-serve: ## Serve documentation locally (MkDocs)
	cd docs && uv run mkdocs serve

docs-build: ## Build documentation site
	cd docs && uv run mkdocs build
