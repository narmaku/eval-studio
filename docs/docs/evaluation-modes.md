# Evaluation Modes

eval-studio supports four evaluation modes, each designed for a different
aspect of AI system assessment. Modes can be used independently or combined
for comprehensive evaluation coverage.

Each mode is implemented as an evaluation adapter that conforms to the
`EvaluationAdapter` interface, making it straightforward to add new modes
or onboard external evaluation frameworks as scoring backends.

## Q&A Benchmark

Run question-answer datasets against any LLM with automated LLM-as-judge
scoring. Ideal for batch evaluation of model knowledge, response quality,
and factual accuracy.

- Upload or import datasets in any format (YAML, JSONL, JSON, CSV)
- Select model under test and judge model independently
- Configure scoring rubrics with custom dimensions and weights
- Live progress and logs streamed via WebSocket
- Results with per-item scores, pass/fail, and judge reasoning

## RAG Evaluation

Evaluate retrieval-augmented generation pipelines with context relevance,
faithfulness, and answer quality metrics.

- Connect to HTTP-based RAG backends or pgvector databases
- Score retrieved chunks alongside generated answers
- Multiple metrics: faithfulness, relevance, answer quality
- Per-chunk visibility into retrieval quality

## Interactive Agent

Live multi-turn conversations with AI agents. Watch tool calls in
real-time, score sessions on task completion and quality.

- WebSocket-powered live chat sessions
- Tool-call observation and timeline
- Session scoring with configurable judges
- Environment provisioning (Docker, BYOE, Testing Farm)

## Model Arena

Run the same evaluation across multiple models side-by-side. Compare
scores in a visual leaderboard with per-question drill-down.

- Select 2-8 contestant models
- Same dataset and judge applied to all contestants
- Per-contestant error isolation (one failure doesn't stop others)
- Ranked leaderboard with color-coded scores
- Side-by-side answer comparison grid

!!! note "Evaluation Framework Integration"
    eval-studio's adapter architecture is designed to onboard external
    evaluation frameworks as scoring backends. lightspeed-evaluation is
    the first target integration. The pluggable design means any framework
    that can score a question-answer pair can be used as an evaluator.
