"""Unit tests for the AsyncRateLimiter utility."""

import asyncio
import time

import pytest

from app.core.rate_limiter import AsyncRateLimiter


class TestAsyncRateLimiterInit:
    def test_creates_with_request_limit(self):
        """RateLimiter accepts request-based rate limits."""
        limiter = AsyncRateLimiter([{"value": 10, "unit": "requests", "per": "minute"}])
        assert limiter is not None

    def test_creates_with_token_limit(self):
        """RateLimiter accepts token-based rate limits."""
        limiter = AsyncRateLimiter([{"value": 1000, "unit": "tokens", "per": "minute"}])
        assert limiter is not None

    def test_creates_with_multiple_limits(self):
        """RateLimiter accepts multiple rate limit rules."""
        limiter = AsyncRateLimiter(
            [
                {"value": 10, "unit": "requests", "per": "minute"},
                {"value": 1000, "unit": "tokens", "per": "minute"},
            ]
        )
        assert limiter is not None

    def test_creates_with_empty_limits(self):
        """RateLimiter with empty limits does not throttle."""
        limiter = AsyncRateLimiter([])
        assert limiter is not None

    def test_creates_with_different_time_windows(self):
        """RateLimiter supports second, minute, hour, day windows."""
        for per in ("second", "minute", "hour", "day"):
            limiter = AsyncRateLimiter([{"value": 5, "unit": "requests", "per": per}])
            assert limiter is not None


class TestAsyncRateLimiterAcquire:
    @pytest.mark.asyncio
    async def test_acquire_within_limit_does_not_block(self):
        """Acquiring within the rate limit should return immediately."""
        limiter = AsyncRateLimiter([{"value": 5, "unit": "requests", "per": "second"}])

        start = time.monotonic()
        for _ in range(5):
            await limiter.acquire()
        elapsed = time.monotonic() - start

        # Should complete nearly instantly (well under 1 second)
        assert elapsed < 0.5

    @pytest.mark.asyncio
    async def test_acquire_exceeding_limit_delays(self):
        """Acquiring beyond the rate limit should delay execution."""
        # 2 requests per second: after 2 requests, the 3rd must wait ~1s
        limiter = AsyncRateLimiter([{"value": 2, "unit": "requests", "per": "second"}])

        # Exhaust the limit
        await limiter.acquire()
        await limiter.acquire()

        # The 3rd acquire should block until the window slides
        start = time.monotonic()
        await limiter.acquire()
        elapsed = time.monotonic() - start

        # Should have waited at least ~0.5s (some tolerance for scheduling)
        assert elapsed >= 0.3

    @pytest.mark.asyncio
    async def test_acquire_token_tracking(self):
        """Token-based limits track cumulative tokens per window."""
        # 100 tokens per second
        limiter = AsyncRateLimiter([{"value": 100, "unit": "tokens", "per": "second"}])

        # Use 60 tokens
        await limiter.acquire(tokens=60)
        # Use 40 more (should fit within the 100 budget)
        start = time.monotonic()
        await limiter.acquire(tokens=40)
        elapsed = time.monotonic() - start
        assert elapsed < 0.5

    @pytest.mark.asyncio
    async def test_acquire_token_exceeds_window_delays(self):
        """Token-based acquire beyond budget delays until window slides."""
        # 50 tokens per second
        limiter = AsyncRateLimiter([{"value": 50, "unit": "tokens", "per": "second"}])

        # Use all 50 tokens
        await limiter.acquire(tokens=50)

        # Next acquire should wait ~1s for the window to slide
        start = time.monotonic()
        await limiter.acquire(tokens=10)
        elapsed = time.monotonic() - start
        assert elapsed >= 0.3

    @pytest.mark.asyncio
    async def test_context_manager_usage(self):
        """AsyncRateLimiter can be used as async context manager."""
        limiter = AsyncRateLimiter([{"value": 5, "unit": "requests", "per": "second"}])

        async with limiter:
            pass  # Should not raise

    @pytest.mark.asyncio
    async def test_empty_limits_never_blocks(self):
        """With no rate limit rules, acquire always succeeds instantly."""
        limiter = AsyncRateLimiter([])

        start = time.monotonic()
        for _ in range(100):
            await limiter.acquire()
        elapsed = time.monotonic() - start

        assert elapsed < 0.5

    @pytest.mark.asyncio
    async def test_multiple_rules_enforced(self):
        """When multiple rules exist, all must be satisfied."""
        # 5 requests/second AND 3 requests/second -- the stricter wins
        limiter = AsyncRateLimiter(
            [
                {"value": 5, "unit": "requests", "per": "second"},
                {"value": 3, "unit": "requests", "per": "second"},
            ]
        )

        # 3 acquires should be fine
        for _ in range(3):
            await limiter.acquire()

        # 4th should delay (stricter limit of 3/s reached)
        start = time.monotonic()
        await limiter.acquire()
        elapsed = time.monotonic() - start
        assert elapsed >= 0.3

    @pytest.mark.asyncio
    async def test_concurrent_acquire_respects_limit(self):
        """Concurrent callers collectively respect the rate limit."""
        limiter = AsyncRateLimiter([{"value": 3, "unit": "requests", "per": "second"}])

        timestamps: list[float] = []

        async def worker():
            await limiter.acquire()
            timestamps.append(time.monotonic())

        # Fire 6 workers concurrently (limit is 3/sec, so ~2 batches)
        await asyncio.gather(*[worker() for _ in range(6)])

        # All 6 should complete
        assert len(timestamps) == 6

        # At least some should have been delayed
        span = timestamps[-1] - timestamps[0]
        assert span >= 0.3
