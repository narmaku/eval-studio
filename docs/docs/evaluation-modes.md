# Evaluation Modes

eval-studio supports four evaluation modes, each designed for a different
aspect of AI system assessment. Modes can be used independently or combined
for comprehensive evaluation coverage.

The four modes are: Q&A Benchmark, RAG Evaluation, Interactive Agent, and
Model Comparison. Each mode is implemented as an evaluation adapter that
conforms to the `EvaluationAdapter` interface, making it straightforward
to add new modes as evaluation needs evolve.

!!! note "Coming soon"
    Detailed documentation for each evaluation mode -- including configuration
    options, scoring dimensions, and example workflows -- will be added as the
    evaluation adapters are implemented. See the [Adapters](adapters.md) page
    for the adapter architecture overview.
