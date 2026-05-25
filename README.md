# eval-studio

The IDE for AI evaluation — one interactive workspace where the UI adapts to what you're testing: Q&A, RAG, agents, MCP servers, or model comparison.

## Overview

eval-studio is an interactive web application for evaluating AI systems. The UI adapts its interaction mode based on what you're evaluating:

- **Q&A Evaluation**: Upload a dataset, pick a judge, see scored results
- **Agent Chat**: Start live multi-turn conversations, watch tool calls in real-time, score sessions
- **RAG Evaluation**: Submit queries, see retrieved chunks alongside generated answers, score faithfulness and relevance
- **Model Arena**: Run the same evaluation across multiple models side-by-side

## Tech Stack

- **Frontend**: React 19 + TypeScript, Vite, shadcn/ui + Tailwind CSS, Zustand
- **Backend**: FastAPI (Python 3.11+), SQLAlchemy 2.0, SQLite (MVP)
- **LLM Access**: LiteLLM proxy (100+ providers)

## Development

```bash
# Backend
cd backend && uv sync && uv run uvicorn app.main:app --reload --port 8000

# Frontend
cd frontend && npm install && npm run dev

# Or via Make
make dev
```

## License

Apache 2.0
