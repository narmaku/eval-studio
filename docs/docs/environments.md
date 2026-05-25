# Environments

Environments are the target machines where AI agents perform tasks during
interactive evaluation. eval-studio supports multiple environment providers
to give you flexibility in how evaluation environments are provisioned
and managed.

Supported providers include Docker Compose (local containers), BYOE (Bring
Your Own Environment via SSH), and TMT (Testing Farm API for real RHEL
virtual machines). Each provider implements the `EnvironmentProvider`
interface for consistent lifecycle management.

!!! note "Coming soon"
    Detailed documentation for each environment provider -- including setup
    instructions, scenario definitions, and troubleshooting guides -- will be
    added as the environment subsystem is implemented. See the
    `environments/` directory in the repository for scenario templates and
    Docker Compose examples.
