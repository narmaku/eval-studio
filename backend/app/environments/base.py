from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


@dataclass
class EnvironmentStatus:
    """Status of a provisioned environment."""

    env_id: str
    status: str  # "provisioning", "ready", "error", "teardown"
    connection_details: dict[str, Any] | None = None
    error_message: str | None = None


@dataclass
class HealthCheckResult:
    """Result of an environment health check."""

    healthy: bool
    checks: list[dict[str, Any]] = field(default_factory=list)  # [{name, passed, output}]


@dataclass
class ConnectionDetails:
    """SSH connection details for an environment."""

    host: str
    port: int = 22
    user: str = "root"
    key_path: str | None = None


class EnvironmentProvider(ABC):
    """Base interface for environment provisioning."""

    @abstractmethod
    async def provision(self, config: dict[str, Any]) -> EnvironmentStatus:
        """Provision a new environment from configuration."""
        ...

    @abstractmethod
    async def health_check(self, env_id: str) -> HealthCheckResult:
        """Run health checks on an environment."""
        ...

    @abstractmethod
    async def teardown(self, env_id: str) -> None:
        """Tear down a provisioned environment."""
        ...

    @abstractmethod
    async def get_connection(self, env_id: str) -> ConnectionDetails:
        """Get SSH connection details for an environment."""
        ...
