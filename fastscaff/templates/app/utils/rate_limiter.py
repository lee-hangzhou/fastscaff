import asyncio
import time
from typing import Callable, Dict, Optional

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.logger import logger
from app.exceptions.base import AppError
from app.exceptions.codes import ErrInternal, ErrTooManyRequests
from app.exceptions.handlers import build_error_response, log_app_error


class TokenBucket:
    """Token bucket algorithm for rate limiting."""

    def __init__(self, capacity: int, refill_rate: float) -> None:
        self.capacity = capacity
        self.refill_rate = refill_rate
        self.tokens = float(capacity)
        self.last_refill = time.monotonic()
        self._lock = asyncio.Lock()

    async def acquire(self, tokens: int = 1) -> bool:
        """Try to acquire tokens. Returns True if successful."""
        async with self._lock:
            now = time.monotonic()
            elapsed = now - self.last_refill

            self.tokens = min(
                self.capacity,
                self.tokens + elapsed * self.refill_rate
            )
            self.last_refill = now

            if self.tokens >= tokens:
                self.tokens -= tokens
                return True

            return False

    @property
    def retry_after(self) -> float:
        """Seconds until at least one token is available."""
        if self.tokens >= 1:
            return 0
        return (1 - self.tokens) / self.refill_rate


class MemoryRateLimiter:
    """In-memory rate limiter using token bucket algorithm."""

    def __init__(
        self,
        requests_per_second: float = 10,
        burst_size: Optional[int] = None,
        key_func: Optional[Callable[[Request], str]] = None,
        cleanup_interval: int = 300,
    ) -> None:
        self.requests_per_second = requests_per_second
        self.burst_size = burst_size or int(requests_per_second * 2)
        self.key_func = key_func or self._default_key_func
        self.cleanup_interval = cleanup_interval

        self._buckets: Dict[str, TokenBucket] = {}
        self._buckets_lock = asyncio.Lock()
        self._last_cleanup = time.monotonic()

    @staticmethod
    def _default_key_func(request: Request) -> str:
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            return forwarded.split(",")[0].strip()

        if request.client:
            return request.client.host

        return "unknown"

    async def _get_bucket(self, key: str) -> TokenBucket:
        async with self._buckets_lock:
            if key not in self._buckets:
                self._buckets[key] = TokenBucket(
                    capacity=self.burst_size,
                    refill_rate=self.requests_per_second,
                )

            await self._maybe_cleanup()

            return self._buckets[key]

    async def _maybe_cleanup(self) -> None:
        now = time.monotonic()
        if now - self._last_cleanup < self.cleanup_interval:
            return

        self._last_cleanup = now
        threshold = now - self.cleanup_interval

        expired_keys = [
            key for key, bucket in self._buckets.items()
            if bucket.last_refill < threshold
        ]

        for key in expired_keys:
            del self._buckets[key]

        if expired_keys:
            logger.debug(
                "Rate limiter cleanup",
                removed=len(expired_keys),
            )

    async def check(self, request: Request) -> None:
        """Raise AppError when rate limit exceeded."""
        key = self.key_func(request)
        bucket = await self._get_bucket(key)

        if not await bucket.acquire():
            raise ErrTooManyRequests.new()

    async def __call__(self, request: Request) -> None:
        await self.check(request)


class RedisRateLimiter:
    """Distributed rate limiter using Redis with sliding window algorithm."""

    def __init__(
        self,
        redis,
        requests_per_window: int = 100,
        window_seconds: int = 60,
        key_prefix: str = "ratelimit",
        key_func: Optional[Callable[[Request], str]] = None,
        fail_open: bool = True,
    ) -> None:
        self.redis = redis
        self.requests_per_window = requests_per_window
        self.window_seconds = window_seconds
        self.key_prefix = key_prefix
        self.key_func = key_func or self._default_key_func
        self.fail_open = fail_open

    @staticmethod
    def _default_key_func(request: Request) -> str:
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            return forwarded.split(",")[0].strip()

        if request.client:
            return request.client.host

        return "unknown"

    async def check(self, request: Request) -> None:
        """Raise AppError when rate limit exceeded."""
        key = f"{self.key_prefix}:{self.key_func(request)}"
        now = time.time()
        window_start = now - self.window_seconds

        try:
            async with self.redis.client.pipeline(transaction=True) as pipe:
                pipe.zremrangebyscore(key, 0, window_start)
                pipe.zadd(key, {str(now): now})
                pipe.zcard(key)
                pipe.expire(key, self.window_seconds + 1)
                results = await pipe.execute()

            request_count = results[2]

            if request_count > self.requests_per_window:
                raise ErrTooManyRequests.new()

        except AppError:
            raise
        except (ConnectionError, TimeoutError, OSError) as e:
            # Intentional fail-open when Redis is unavailable (unless configured otherwise).
            logger.error("redis rate limiter error", exc=e)
            if not self.fail_open:
                raise ErrInternal.wrap(e, "Rate limiting service unavailable") from e

    async def __call__(self, request: Request) -> None:
        await self.check(request)


class RateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(
        self,
        app,
        limiter,
        exclude_paths: Optional[list[str]] = None,
    ) -> None:
        super().__init__(app)
        self.limiter = limiter
        self.exclude_paths = set(exclude_paths or [])

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        if request.url.path in self.exclude_paths:
            return await call_next(request)

        try:
            await self.limiter.check(request)
        except AppError as exc:
            log_app_error(request, exc)
            return build_error_response(exc)

        return await call_next(request)
