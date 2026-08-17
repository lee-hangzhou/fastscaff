import asyncio
import hashlib
import json
import time
from collections import OrderedDict
from collections.abc import Awaitable, Coroutine
from typing import Any, Callable, Dict, Optional, Tuple, TypeVar

from app.core.logger import logger

T = TypeVar("T")
AsyncFunc = Callable[..., Coroutine[Any, Any, T]]


class CachedFunction:
    """Wrapper for cached async functions."""

    def __init__(
        self,
        func: Callable[..., Awaitable[Any]],
        cache: "MultiLevelCache",
        ttl: int,
        key_builder: Callable[..., str],
        cache_none: bool,
    ) -> None:
        self._original_func = func
        self._cache = cache
        self._ttl = ttl
        self._key_builder = key_builder
        self._cache_none = cache_none
        self.__name__: str = func.__name__ if hasattr(func, "__name__") else "cached_function"
        self.__doc__ = func.__doc__
        self.__module__: str = func.__module__ if hasattr(func, "__module__") else __name__
        self.__qualname__: str = func.__qualname__ if hasattr(func, "__qualname__") else self.__name__

    @property
    def original_func(self) -> Callable[..., Awaitable[Any]]:
        return self._original_func

    async def __call__(self, *args: Any, **kwargs: Any) -> Any:
        cache_key = self._key_builder(*args, **kwargs)

        async def compute() -> Any:
            return await self._original_func(*args, **kwargs)

        return await self._cache.get_or_compute(
            key=cache_key,
            compute_func=compute,
            ttl=self._ttl,
            cache_none=self._cache_none,
        )


class LRUCache:
    """Thread-safe LRU cache with TTL support. Used as L1 cache."""

    def __init__(self, maxsize: int = 1000, default_ttl: int = 300) -> None:
        self.maxsize = maxsize
        self.default_ttl = default_ttl
        self._cache: OrderedDict[str, tuple[Any, float]] = OrderedDict()
        self._lock = asyncio.Lock()

    async def get(self, key: str) -> Optional[Any]:
        async with self._lock:
            if key not in self._cache:
                return None

            value, expires_at = self._cache[key]

            if expires_at and time.time() > expires_at:
                del self._cache[key]
                return None

            self._cache.move_to_end(key)
            return value

    async def set(
        self,
        key: str,
        value: Any,
        ttl: Optional[int] = None,
    ) -> None:
        async with self._lock:
            if ttl is None:
                ttl = self.default_ttl

            expires_at = time.time() + ttl if ttl > 0 else 0

            if key in self._cache:
                self._cache.move_to_end(key)
            elif len(self._cache) >= self.maxsize:
                self._cache.popitem(last=False)

            self._cache[key] = (value, expires_at)

    async def delete(self, key: str) -> bool:
        async with self._lock:
            if key in self._cache:
                del self._cache[key]
                return True
            return False

    async def clear(self) -> None:
        async with self._lock:
            self._cache.clear()

    async def cleanup_expired(self) -> int:
        async with self._lock:
            now = time.time()
            expired_keys = [
                key for key, (_, expires_at) in self._cache.items()
                if expires_at and now > expires_at
            ]
            for key in expired_keys:
                del self._cache[key]
            return len(expired_keys)


class MultiLevelCache:
    """Multi-level cache with L1 (local memory) and L2 (Redis)."""

    _NULL_SENTINEL = "__NULL__"

    def __init__(
        self,
        redis=None,
        l1_maxsize: int = 1000,
        l1_ttl: int = 60,
        l2_ttl: int = 300,
        key_prefix: str = "cache",
        null_ttl: int = 30,
        lock_timeout: int = 5,
    ) -> None:
        self.redis = redis
        self.l1 = LRUCache(maxsize=l1_maxsize, default_ttl=l1_ttl)
        self.l1_ttl = l1_ttl
        self.l2_ttl = l2_ttl
        self.key_prefix = key_prefix
        self.null_ttl = null_ttl
        self.lock_timeout = lock_timeout

    def _make_key(self, key: str) -> str:
        return f"{self.key_prefix}:{key}"

    def _make_lock_key(self, key: str) -> str:
        return f"{self.key_prefix}:lock:{key}"

    async def get(self, key: str) -> Optional[Any]:
        l1_value = await self.l1.get(key)
        if l1_value is not None:
            if l1_value == self._NULL_SENTINEL:
                return None
            return l1_value

        if not self.redis:
            return None

        try:
            redis_key = self._make_key(key)
            raw_value = await self.redis.get(redis_key)

            if raw_value is None:
                return None

            value = json.loads(raw_value)

            if value == self._NULL_SENTINEL:
                await self.l1.set(key, self._NULL_SENTINEL, ttl=self.null_ttl)
                return None

            await self.l1.set(key, value, ttl=self.l1_ttl)
            return value

        except Exception as e:
            # Intentional degrade: serve from L1 / miss rather than failing the request.
            logger.error("cache L2 get error", exc=e)
            return None

    async def set(
        self,
        key: str,
        value: Any,
        ttl: Optional[int] = None,
        l1_ttl: Optional[int] = None,
    ) -> bool:
        if ttl is None:
            ttl = self.l2_ttl
        if l1_ttl is None:
            l1_ttl = min(self.l1_ttl, ttl)

        cache_value = self._NULL_SENTINEL if value is None else value

        await self.l1.set(key, cache_value, ttl=l1_ttl)

        if not self.redis:
            return True

        try:
            redis_key = self._make_key(key)
            await self.redis.set(
                redis_key,
                json.dumps(cache_value, default=str),
                ex=ttl,
            )
            return True
        except Exception as e:
            # Intentional degrade: L1 still updated; L2 write failure is non-fatal.
            logger.error("cache L2 set error", exc=e)
            return False

    async def delete(self, key: str) -> bool:
        await self.l1.delete(key)

        if not self.redis:
            return True

        try:
            redis_key = self._make_key(key)
            await self.redis.delete(redis_key)
            return True
        except Exception as e:
            # Intentional degrade: L1 deleted; L2 delete failure is non-fatal.
            logger.error("cache L2 delete error", exc=e)
            return False

    async def _acquire_lock(self, key: str) -> bool:
        if not self.redis:
            return True

        try:
            lock_key = self._make_lock_key(key)
            acquired = await self.redis.set(
                lock_key,
                "1",
                ex=self.lock_timeout,
                nx=True,
            )
            return bool(acquired)
        except Exception as e:
            # Intentional fail-open: allow execution if lock acquisition fails.
            logger.error("cache lock acquire failed", exc=e, key=key)
            return True

    async def _release_lock(self, key: str) -> None:
        if not self.redis:
            return

        try:
            lock_key = self._make_lock_key(key)
            await self.redis.delete(lock_key)
        except Exception as e:
            # Lock will expire anyway; keep primary path succeeding.
            logger.error("cache lock release failed", exc=e, key=key)

    async def get_or_set(
        self,
        key: str,
        factory: Callable[[], Any],
        ttl: Optional[int] = None,
    ) -> Any:
        value = await self.get(key)
        if value is not None:
            return value

        if not await self._acquire_lock(key):
            await asyncio.sleep(0.1)
            value = await self.get(key)
            if value is not None:
                return value

        try:
            if asyncio.iscoroutinefunction(factory):
                value = await factory()
            else:
                value = factory()

            await self.set(key, value, ttl=ttl)
            return value
        finally:
            await self._release_lock(key)

    async def get_or_compute(
        self,
        key: str,
        compute_func: Callable[[], Awaitable[Any]],
        ttl: Optional[int] = None,
        cache_none: bool = True,
    ) -> Any:
        cached_value = await self.get(key)
        if cached_value is not None:
            return cached_value

        # Check if None was explicitly cached
        l1_value = await self.l1.get(key)
        if l1_value == self._NULL_SENTINEL:
            return None

        # Try to acquire lock for cache stampede protection
        if not await self._acquire_lock(key):
            await asyncio.sleep(0.05)
            cached_value = await self.get(key)
            if cached_value is not None:
                return cached_value
            l1_value = await self.l1.get(key)
            if l1_value == self._NULL_SENTINEL:
                return None

        try:
            result = await compute_func()

            if result is not None or cache_none:
                await self.set(key, result, ttl=ttl)

            return result
        finally:
            await self._release_lock(key)

    def cached(
        self,
        ttl: Optional[int] = None,
        key_builder: Optional[Callable[..., str]] = None,
        cache_none: bool = True,
    ) -> Callable[[Callable[..., Awaitable[Any]]], CachedFunction]:
        effective_ttl = ttl if ttl is not None else self.l2_ttl
        cache_instance = self

        def decorator(func: Callable[..., Awaitable[Any]]) -> CachedFunction:
            if key_builder is not None:
                actual_key_builder = key_builder
            else:
                def actual_key_builder(*args: Any, **kwargs: Any) -> str:
                    return cache_instance.make_cache_key(func, args, kwargs)

            return CachedFunction(
                func=func,
                cache=cache_instance,
                ttl=effective_ttl,
                key_builder=actual_key_builder,
                cache_none=cache_none,
            )

        return decorator

    @staticmethod
    def make_cache_key(
        func: Callable[..., Any],
        args: Tuple[Any, ...],
        kwargs: Dict[str, Any],
    ) -> str:
        key_parts = [
            func.__module__,
            func.__qualname__,
            str(args),
            str(sorted(kwargs.items())),
        ]
        key_hash = hashlib.sha256(
            json.dumps(key_parts, default=str).encode()
        ).hexdigest()[:16]
        return f"func:{func.__qualname__}:{key_hash}"

    async def invalidate(
        self,
        func: Callable[..., Any],
        *args: Any,
        **kwargs: Any,
    ) -> bool:
        if isinstance(func, CachedFunction):
            original_func = func.original_func
        else:
            original_func = func
        cache_key = self.make_cache_key(original_func, args, kwargs)
        return await self.delete(cache_key)

    async def invalidate_pattern(self, pattern: str) -> int:
        if not self.redis:
            return 0

        try:
            full_pattern = self._make_key(pattern)
            keys = []

            async for key in self.redis.client.scan_iter(match=full_pattern):
                keys.append(key)

            if keys:
                await self.redis.client.delete(*keys)

            return len(keys)
        except Exception as e:
            logger.error("cache invalidate_pattern error", exc=e)
            return 0


def create_cache(redis=None) -> MultiLevelCache:
    return MultiLevelCache(redis=redis)
