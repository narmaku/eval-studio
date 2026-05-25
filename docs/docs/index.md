# eval-studio

**The IDE for AI evaluation.**

eval-studio is an interactive web application for evaluating AI systems against
real-world scenarios. It bridges the gap between static benchmarks and
production-ready AI assessment.

## Evaluation Modes

eval-studio supports four evaluation modes, each designed for a different
stage of the AI development lifecycle:

- **Q&A Benchmark**: Run question-answer datasets against models with
  automated LLM-as-judge scoring. Great for batch evaluation of model
  knowledge.

- **RAG Evaluation**: Evaluate retrieval-augmented generation pipelines
  with context relevance, faithfulness, and answer quality metrics.

- **Interactive Agent**: Watch AI agents solve real sysadmin tasks in
  live Linux environments. Agents connect via SSH and are evaluated on
  their ability to diagnose and fix issues.

- **Model Comparison**: Run the same evaluation across multiple models
  side-by-side. Compare scores, costs, and latency in a unified view.

## Key Features

- **Pluggable Adapters**: Swap evaluation backends without changing your
  workflow. Each evaluation mode is implemented as an adapter that
  conforms to a standard interface.

- **Real Environment Provisioning**: Spin up Docker containers, connect
  to existing machines via SSH (BYOE), or provision real RHEL VMs via
  Testing Farm. Scenarios define the "broken" state for agents to fix.

- **LLM-as-Judge Scoring**: Use any LLM (via LiteLLM) as an evaluation
  judge. Configure single-model or multi-model panel judges with
  customizable scoring dimensions.

- **Real-Time Interaction**: WebSocket-powered live chat with agents,
  streaming evaluation progress, and collaborative features.

## Quick Start

See the [Getting Started](getting-started.md) guide to set up your
development environment and run your first evaluation.
