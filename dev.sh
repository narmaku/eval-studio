#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_PID=""
FRONTEND_PID=""

cleanup() {
    echo ""
    echo "Shutting down..."
    [[ -n "$FRONTEND_PID" ]] && kill "$FRONTEND_PID" 2>/dev/null && wait "$FRONTEND_PID" 2>/dev/null
    [[ -n "$BACKEND_PID" ]]  && kill "$BACKEND_PID"  2>/dev/null && wait "$BACKEND_PID"  2>/dev/null
    echo "Done."
}

trap cleanup EXIT INT TERM

# Load .env if present (exports vars so LiteLLM and subprocesses see them)
if [[ -f "$SCRIPT_DIR/.env" ]]; then
    set -a
    source "$SCRIPT_DIR/.env"
    set +a
    echo "Loaded .env"
else
    echo "Warning: no .env file found. Copy .env.example and add your API keys:"
    echo "  cp .env.example .env"
fi

echo "=== eval-studio dev ==="

# Backend
echo "Starting backend on :8000..."
cd "$SCRIPT_DIR/backend"
uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000 &
BACKEND_PID=$!

# Frontend
echo "Starting frontend on :5173..."
cd "$SCRIPT_DIR/frontend"
npm run dev -- --host 0.0.0.0 &
FRONTEND_PID=$!

echo ""
echo "  Backend:  http://localhost:8000/docs"
echo "  Frontend: http://localhost:5173"
echo ""
echo "Press Ctrl+C to stop both."
echo ""

wait
