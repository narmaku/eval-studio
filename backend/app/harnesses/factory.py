"""Factory functions for creating harness instances and output parsers."""

from app.harnesses.base import AgentHarness
from app.harnesses.parsers.base import DefaultOutputParser, OutputParser
from app.harnesses.registry import harness_registry


def create_harness(harness_id: str) -> AgentHarness:
    """Create an AgentHarness instance by harness id.

    Args:
        harness_id: The id of the harness profile to instantiate.

    Returns:
        An initialized AgentHarness.

    Raises:
        ValueError: If the harness_id is unknown or has an unsupported type.
    """
    profile = harness_registry.get_harness(harness_id)
    if not profile:
        raise ValueError(f"Unknown harness: {harness_id}")

    if profile.type == "subprocess":
        from app.harnesses.subprocess_harness import SubprocessHarness

        return SubprocessHarness(profile)
    else:
        raise ValueError(f"Unknown harness type: {profile.type}")


def get_parser(output_format: str | None) -> OutputParser:
    """Get an output parser by format name.

    Args:
        output_format: The format identifier (e.g. "goose"), or None for default.

    Returns:
        An OutputParser instance.
    """
    if output_format == "goose":
        from app.harnesses.parsers.goose import GooseOutputParser

        return GooseOutputParser()
    # Default: line-by-line text parser
    return DefaultOutputParser()
