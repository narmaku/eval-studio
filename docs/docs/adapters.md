# Adapters

eval-studio uses an adapter pattern for both evaluation backends and
environment providers. This architecture makes the system extensible:
new evaluation modes or environment types can be added by implementing
a well-defined interface without modifying existing code.

Evaluation adapters implement the `EvaluationAdapter` abstract base class
defined in `backend/app/adapters/base.py`. Environment providers implement
the `EnvironmentProvider` ABC in `backend/app/environments/base.py`.

!!! note "Coming soon"
    Detailed API documentation for the adapter interfaces, including method
    signatures, configuration schemas, and implementation examples, will be
    added as the backend foundation is built. See the
    [CONTRIBUTING.md](https://github.com/narmaku/eval-studio/blob/main/CONTRIBUTING.md)
    for a quick guide on adding new adapters.
