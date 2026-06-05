"""Subprocess harness — runs an external CLI agent and parses its output."""

import asyncio
import contextlib
from collections.abc import AsyncGenerator
from typing import Any

import structlog

from app.core.config import settings
from app.core.exceptions import sanitize_error_for_client
from app.core.subprocess_validation import load_allowed_commands, validate_command
from app.harnesses.base import AgentHarness, HarnessEvent
from app.harnesses.factory import get_parser
from app.harnesses.registry import HarnessProfile

logger = structlog.get_logger()

DEFAULT_TIMEOUT_SECONDS = 30


class SubprocessHarness(AgentHarness):
    """Run an external CLI agent as a subprocess and parse its output."""

    def __init__(self, profile: HarnessProfile) -> None:
        self._profile = profile
        self._config: dict[str, Any] = {}
        self._process: asyncio.subprocess.Process | None = None

    @property
    def supports_streaming(self) -> bool:
        return "streaming" in self._profile.supported_features

    @property
    def supports_tool_calls(self) -> bool:
        return "tool_calls" in self._profile.supported_features

    async def start_session(self, config: dict[str, Any]) -> None:
        """Validate binary exists, is allowed, and store config."""
        binary = self._profile.binary_path
        if not binary:
            raise ValueError(f"Harness '{self._profile.id}' has no binary_path configured")

        allowed = load_allowed_commands(settings.harness_allowed_binaries)
        resolved = validate_command(binary, allowed, context="harness binary")

        self._config = config
        logger.info(
            "subprocess_harness.session_started",
            harness_id=self._profile.id,
            binary=resolved,
        )

    async def send_message(self, content: str, history: list[dict[str, Any]]) -> AsyncGenerator[HarnessEvent, None]:
        """Spawn the subprocess, write prompt to stdin, parse stdout."""
        binary = self._profile.binary_path
        if not binary:
            yield HarnessEvent(type="error", data={"message": "No binary_path configured"})
            return

        cmd = [binary, *self._profile.args]

        # Build prompt from history summary + current message
        prompt = self._build_prompt(content, history)

        # Merge environment
        env = {**self._profile.env} if self._profile.env else None

        parser = get_parser(self._profile.output_format)
        timeout = self._config.get("timeout", DEFAULT_TIMEOUT_SECONDS)

        try:
            self._process = await asyncio.create_subprocess_exec(
                *cmd,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env=env if env else None,
            )

            # Write prompt to stdin and close
            if self._process.stdin:
                self._process.stdin.write(prompt.encode())
                await self._process.stdin.drain()
                self._process.stdin.close()

            # Read stdout line-by-line
            full_content = ""
            if self._process.stdout:
                try:
                    while True:
                        line_bytes = await asyncio.wait_for(
                            self._process.stdout.readline(),
                            timeout=timeout,
                        )
                        if not line_bytes:
                            break
                        line = line_bytes.decode(errors="replace")
                        events = parser.parse_line(line)
                        for event in events:
                            if event.type == "message_chunk":
                                full_content += event.data.get("content", "")
                            yield event
                except TimeoutError:
                    logger.warning(
                        "subprocess_harness.timeout",
                        harness_id=self._profile.id,
                        timeout=timeout,
                    )
                    yield HarnessEvent(
                        type="error",
                        data={"message": f"Subprocess timed out after {timeout}s"},
                    )

            # Flush parser buffer
            for event in parser.flush():
                if event.type == "message_chunk":
                    full_content += event.data.get("content", "")
                yield event

            # Wait for process to complete
            try:
                await asyncio.wait_for(self._process.wait(), timeout=5)
            except TimeoutError:
                self._process.kill()
                await self._process.wait()

            # Check for errors on stderr
            if self._process.stderr:
                stderr_bytes = await self._process.stderr.read()
                stderr_text = stderr_bytes.decode(errors="replace").strip()
                if stderr_text and self._process.returncode != 0:
                    logger.warning(
                        "subprocess_harness.stderr",
                        harness_id=self._profile.id,
                        stderr=stderr_text[:500],
                    )

            # Emit message_complete
            yield HarnessEvent(
                type="message_complete",
                data={"content": full_content.strip(), "tool_calls": []},
            )

        except FileNotFoundError:
            yield HarnessEvent(
                type="error",
                data={"message": f"Binary '{binary}' not found"},
            )
        except Exception as exc:
            logger.exception("subprocess_harness.error", harness_id=self._profile.id)
            yield HarnessEvent(
                type="error",
                data={"message": f"Subprocess error: {sanitize_error_for_client(exc)}"},
            )
        finally:
            self._process = None

    async def stop_session(self) -> None:
        """Terminate the subprocess if still running."""
        if self._process and self._process.returncode is None:
            try:
                self._process.terminate()
                await asyncio.wait_for(self._process.wait(), timeout=5)
            except (TimeoutError, ProcessLookupError):
                with contextlib.suppress(ProcessLookupError):
                    self._process.kill()
            self._process = None
        self._config = {}

    def _build_prompt(self, content: str, history: list[dict[str, Any]]) -> str:
        """Build a text prompt from the current message and recent history."""
        parts: list[str] = []

        # Include a brief history summary (last 5 messages)
        recent = history[-5:] if len(history) > 5 else history
        if recent:
            parts.append("--- Conversation History ---")
            for msg in recent:
                role = msg.get("role", "unknown")
                text = msg.get("content", "")
                if text:
                    parts.append(f"{role}: {text}")
            parts.append("--- End History ---\n")

        parts.append(content)
        return "\n".join(parts) + "\n"
