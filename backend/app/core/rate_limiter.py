"""Async rate limiter for throttling evaluation requests.

Uses a sliding window approach to enforce rate limits defined as
JSON rules on provider profiles. Supports both request-based and
token-based limits with configurable time windows.
"""

import asyncio
import time
from collections import deque

# Map time window names to seconds.
_WINDOW_SECONDS = {
    "second": 1,
    "minute": 60,
    "hour": 3600,
    "day": 86400,
}


class _SlidingWindowRule:
    """A single sliding-window rate limit rule.

    Tracks timestamps (and token counts) of recent requests within a
    rolling time window. When the budget is exhausted, callers sleep
    until the oldest entry falls outside the window.
    """

    def __init__(self, value: int, unit: str, window_seconds: float):
        self.value = value
        self.unit = unit  # "requests" or "tokens"
        self.window_seconds = window_seconds
        self._lock = asyncio.Lock()
        # Each entry is (timestamp, cost) where cost=1 for requests, token count for tokens
        self._entries: deque[tuple[float, int]] = deque()
        self._current_total: int = 0

    def _evict_expired(self, now: float) -> None:
        """Remove entries that have fallen outside the window."""
        cutoff = now - self.window_seconds
        while self._entries and self._entries[0][0] <= cutoff:
            _, cost = self._entries.popleft()
            self._current_total -= cost

    async def acquire(self, cost: int = 1) -> None:
        """Wait until this rule allows the request, then record it."""
        while True:
            async with self._lock:
                now = time.monotonic()
                self._evict_expired(now)

                if self._current_total + cost <= self.value:
                    # Budget available — record and proceed
                    self._entries.append((now, cost))
                    self._current_total += cost
                    return

                # Budget exhausted — calculate sleep until oldest entry expires
                if self._entries:
                    oldest_ts = self._entries[0][0]
                    sleep_time = (oldest_ts + self.window_seconds) - now
                else:
                    sleep_time = self.window_seconds

            # Sleep outside the lock so other coroutines aren't blocked
            await asyncio.sleep(max(sleep_time, 0.01))


class AsyncRateLimiter:
    """Async rate limiter that enforces multiple rate limit rules.

    Each rule is a dict with keys: value (int), unit ("requests" or "tokens"),
    per ("second", "minute", "hour", "day").

    Usage::

        limiter = AsyncRateLimiter([
            {"value": 10, "unit": "requests", "per": "minute"},
            {"value": 1000, "unit": "tokens", "per": "minute"},
        ])

        # Before each LLM call:
        await limiter.acquire()

        # Or as a context manager (for request-based limits):
        async with limiter:
            await call_model(...)
    """

    def __init__(self, rate_limits: list[dict]) -> None:
        self._rules: list[_SlidingWindowRule] = []
        for limit in rate_limits:
            window_seconds = _WINDOW_SECONDS.get(limit["per"], 60)
            self._rules.append(
                _SlidingWindowRule(
                    value=limit["value"],
                    unit=limit["unit"],
                    window_seconds=window_seconds,
                )
            )

    async def acquire(self, tokens: int = 1) -> None:
        """Wait until all rate limit rules allow the request.

        Args:
            tokens: Number of tokens to consume (used for token-based limits).
                    Request-based limits always consume 1 regardless of this value.
        """
        for rule in self._rules:
            cost = tokens if rule.unit == "tokens" else 1
            await rule.acquire(cost)

    async def __aenter__(self) -> "AsyncRateLimiter":
        await self.acquire()
        return self

    async def __aexit__(self, *args: object) -> None:
        pass
