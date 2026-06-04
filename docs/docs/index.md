# eval-studio

**The workspace for building, running, and improving AI evaluations.**

eval-studio goes beyond running AI evaluations. It is a complete workspace for
building everything needed to evaluate AI systems successfully — datasets,
scoring metrics, evaluation rubrics, and telemetry integrations — then using
them seamlessly with any evaluation framework onboarded into the platform.

Designed for engineers and non-technical subject-matter experts alike,
eval-studio helps teams iterate on AI tooling and AI products with
confidence.

## What You Can Do

- **Build datasets** — Import from any format (YAML, JSONL, JSON, CSV).
  Smart import auto-detects fields and suggests mappings. Upload entire
  directories. Supports lightspeed-evaluation, SQuAD, Alpaca, and custom
  formats out of the box.

- **Design scoring rubrics** — Create evaluation dimensions with
  AI-assisted generation via rubric-kit. Refine rubrics with feedback,
  compare scoring approaches, import from rubric-kit YAML.

- **Configure LLM providers** — Register any model endpoint
  (OpenAI-compatible, LiteLLM-backed). API keys managed via environment
  variables, never stored directly.

- **Run evaluations** — Q&A benchmarks, RAG pipelines, interactive
  agent sessions, or side-by-side model arena. Live logs and progress
  streamed via WebSocket.

- **Compare and iterate** — Arena mode for head-to-head model comparison
  with visual leaderboards. Per-question drill-down across contestants.

- **Plug in evaluation frameworks** — Adapter architecture supports
  onboarding external evaluation systems as scoring backends.
  lightspeed-evaluation is the first target integration.

## Evaluation Modes

| Mode | Description |
|------|-------------|
| **Q&A Benchmark** | Run datasets against models with LLM-as-judge scoring |
| **RAG Evaluation** | Evaluate retrieval + generation with faithfulness and relevance metrics |
| **Interactive Agent** | Live multi-turn conversations with tool-call observation and scoring |
| **Model Arena** | Same evaluation across multiple models side-by-side with leaderboard |

## Key Features

- **Pluggable Adapters**: Swap evaluation backends without changing your
  workflow. Each evaluation mode is implemented as an adapter that
  conforms to a standard interface.

- **Smart Dataset Import**: Auto-detect file formats and field mappings.
  Upload directories of files. Handles nested structures like
  lightspeed-evaluation's conversation format.

- **AI-Assisted Rubric Design**: Generate scoring rubrics from natural
  language descriptions via rubric-kit. Refine with feedback loops.

- **Live Evaluation Logs**: WebSocket-streamed progress and structured
  logs during evaluation runs. Navigate away and resume — running
  evaluation state persists.

- **Real Environment Provisioning**: Spin up Docker containers, connect
  to existing machines via SSH (BYOE), or provision real RHEL VMs via
  Testing Farm.

- **LLM-as-Judge Scoring**: Use any LLM (via LiteLLM) as an evaluation
  judge. Configure single-model or multi-model panel judges with
  customizable scoring dimensions.

## Security Considerations

eval-studio is designed as a **localhost development tool** and does not
include built-in authentication or authorization. All API endpoints and
WebSocket connections are open by default.

**If you need to expose eval-studio over a network:**

- Place it behind a reverse proxy (e.g., nginx, Caddy, or Envoy) that
  handles authentication.
- Use an SSH tunnel (`ssh -L 8000:localhost:8000 remote-host`) for
  remote access without exposing the service.
- Restrict access at the firewall level so that only trusted networks
  can reach the application ports.

Error messages returned to clients are sanitized to prevent leaking
internal details such as file paths, database connection strings, or
stack traces. Full error information is always available in the
server-side logs.

## Quick Start

See the [Getting Started](getting-started.md) guide to set up your
development environment and run your first evaluation.
