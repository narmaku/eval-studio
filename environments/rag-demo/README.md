# RAG Demo Service

A self-contained sample RAG (Retrieval-Augmented Generation) service for testing
eval-studio's RAG evaluation mode. It performs real vector similarity search over
a corpus of 20 RHEL sysadmin documents and generates answers using an LLM.

## Quick Start

```bash
# Build and start (from the repo root)
docker compose --profile rag up -d

# Check health
curl http://localhost:8100/health

# Query
curl -X POST http://localhost:8100/query \
  -H "Content-Type: application/json" \
  -d '{"query": "How do I check a systemd service?"}'
```

## How It Works

1. On startup the service loads 20 RHEL sysadmin documents, computes embeddings
   with `sentence-transformers/all-MiniLM-L6-v2`, and builds a FAISS index.
2. `POST /query` embeds the query, retrieves the top-5 similar chunks via FAISS,
   and generates an answer with LiteLLM.
3. If no `LITELLM_MODEL` is set, the service still returns retrieved chunks but
   notes that answer generation requires an API key.

## Configuration

| Variable | Description | Default |
|---|---|---|
| `LITELLM_MODEL` | LiteLLM model identifier (e.g. `openai/gpt-4o-mini`) | _(none -- retrieval only)_ |
| `OPENAI_API_KEY` | API key when using an OpenAI model | |
| `ANTHROPIC_API_KEY` | API key when using an Anthropic model | |

## API

### `POST /query`

```json
{"query": "How do I check a systemd service?"}
```

Response:

```json
{
  "answer": "Use 'systemctl status <service-name>' ...",
  "source_documents": [
    {"content": "...", "source": "systemd-services.md"},
    {"content": "...", "source": "journald-logging.md"}
  ]
}
```

### `GET /health`

Returns `200` with status info:

```json
{
  "status": "ok",
  "documents_loaded": 20,
  "index_ready": true,
  "llm_configured": false
}
```
