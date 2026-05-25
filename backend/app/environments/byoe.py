import uuid
from typing import Any

import asyncssh  # noqa: F401 -- imported to verify dependency is available

from app.environments.base import (
    ConnectionDetails,
    EnvironmentProvider,
    EnvironmentStatus,
    HealthCheckResult,
)


class BYOEProvider(EnvironmentProvider):
    """Bring Your Own Environment provider. Connects to pre-provisioned SSH hosts."""

    async def provision(self, config: dict[str, Any]) -> EnvironmentStatus:
        """Register a BYOE environment from user-provided connection details."""
        # TODO: Connect via asyncssh, run health checks, return status
        env_id = str(uuid.uuid4())
        return EnvironmentStatus(
            env_id=env_id,
            status="ready",
            connection_details={"host": config.get("host"), "port": config.get("port", 22)},
        )

    async def health_check(self, env_id: str) -> HealthCheckResult:
        """Run SSH health checks on the environment."""
        # TODO: SSH connect and run health check commands
        return HealthCheckResult(healthy=True, checks=[])

    async def teardown(self, env_id: str) -> None:
        """Run teardown playbook if configured."""
        # TODO: Run teardown playbook if configured
        pass

    async def get_connection(self, env_id: str) -> ConnectionDetails:
        """Look up stored connection details for the environment."""
        # TODO: Look up stored connection details
        raise NotImplementedError("BYOE connection lookup not yet implemented")
