"""Unit tests for SubprocessHarness."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from app.harnesses.registry import HarnessProfile
from app.harnesses.subprocess_harness import SubprocessHarness


@pytest.fixture
def subprocess_profile():
    return HarnessProfile(
        id="test-sub",
        name="Test Subprocess",
        type="subprocess",
        binary_path="echo",
        args=[],
        output_format=None,
        supported_features=["tool_calls"],
    )


@pytest.mark.asyncio
async def test_start_session_validates_binary(subprocess_profile):
    harness = SubprocessHarness(subprocess_profile)
    # echo should be available on most systems
    await harness.start_session({})


@pytest.mark.asyncio
async def test_start_session_binary_not_found():
    profile = HarnessProfile(
        id="bad",
        name="Bad",
        type="subprocess",
        binary_path="__nonexistent_binary_xyz__",
    )
    harness = SubprocessHarness(profile)
    with pytest.raises(FileNotFoundError, match="not found in PATH"):
        await harness.start_session({})


@pytest.mark.asyncio
async def test_start_session_no_binary_path():
    profile = HarnessProfile(
        id="no-bin",
        name="No Bin",
        type="subprocess",
        binary_path=None,
    )
    harness = SubprocessHarness(profile)
    with pytest.raises(ValueError, match="no binary_path"):
        await harness.start_session({})


@pytest.mark.asyncio
async def test_send_message_basic_output(subprocess_profile):
    """Test that send_message captures stdout from a subprocess."""
    harness = SubprocessHarness(subprocess_profile)
    # Use echo command which should be available
    subprocess_profile.binary_path = "echo"
    subprocess_profile.args = ["hello world"]
    await harness.start_session({})

    events = []
    async for event in harness.send_message("test prompt", []):
        events.append(event)

    # Should have at least a message_complete event
    types = [e.type for e in events]
    assert "message_complete" in types

    complete = next(e for e in events if e.type == "message_complete")
    assert "hello world" in complete.data.get("content", "")


@pytest.mark.asyncio
async def test_send_message_binary_not_found_at_runtime():
    """Test error handling when binary disappears between start and send."""
    profile = HarnessProfile(
        id="vanish",
        name="Vanish",
        type="subprocess",
        binary_path="__truly_nonexistent_cmd__",
    )
    harness = SubprocessHarness(profile)
    harness._config = {}  # Skip start_session validation

    events = []
    async for event in harness.send_message("test", []):
        events.append(event)

    error_events = [e for e in events if e.type == "error"]
    assert len(error_events) >= 1
    assert "not found" in error_events[0].data["message"].lower()


@pytest.mark.asyncio
async def test_stop_session_terminates_process(subprocess_profile):
    """Test that stop_session terminates a running process."""
    harness = SubprocessHarness(subprocess_profile)
    await harness.start_session({})

    # Mock a running process
    mock_process = MagicMock()
    mock_process.returncode = None
    mock_process.terminate = MagicMock()
    mock_process.kill = MagicMock()
    mock_process.wait = AsyncMock(return_value=0)
    harness._process = mock_process

    await harness.stop_session()

    mock_process.terminate.assert_called_once()
    assert harness._process is None
