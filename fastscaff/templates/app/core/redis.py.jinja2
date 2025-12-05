import json
from typing import Any, Dict, List, Optional, Set, Union

from redis.asyncio import ConnectionPool, Redis

from app.core.config import settings
from app.core.singleton import Singleton

# Note: redis-py's async methods are typed as returning Union[Awaitable[T], T]
# due to their implementation supporting both sync and async modes.
# In practice, redis.asyncio.Redis methods always return coroutines.
# The type: ignore comments below are for this known redis-py typing limitation.


class RedisClient(Singleton):
    """Async Redis client wrapper with connection pooling."""

    _client: Optional[Redis] = None
    _pool: Optional[ConnectionPool] = None

    async def connect(self) -> None:
        """Establish connection to Redis."""
        if self._client is not None:
            return

        self._pool = ConnectionPool.from_url(
            settings.REDIS_URL,
            max_connections=settings.REDIS_MAX_CONNECTIONS,
            decode_responses=True,
        )
        self._client = Redis(connection_pool=self._pool)

    async def disconnect(self) -> None:
        """Close Redis connection."""
        if self._client:
            await self._client.aclose()
            self._client = None
        if self._pool:
            await self._pool.disconnect()
            self._pool = None

    def _ensure_connected(self) -> Redis:
        """Ensure client is connected and return it."""
        if self._client is None:
            raise RuntimeError("Redis client not connected. Call connect() first.")
        return self._client

    @property
    def client(self) -> Redis:
        """Get the Redis client instance."""
        return self._ensure_connected()

    async def get(self, key: str) -> Optional[str]:
        """Get string value by key."""
        client = self._ensure_connected()
        result = await client.get(key)  # type: ignore[misc]
        if result is None:
            return None
        return result.decode() if isinstance(result, bytes) else str(result)

    async def set(
        self,
        key: str,
        value: Union[str, bytes, int, float],
        ex: Optional[int] = None,
        px: Optional[int] = None,
        nx: bool = False,
        xx: bool = False,
    ) -> Optional[bool]:
        """Set string value with optional expiration."""
        client = self._ensure_connected()
        result = await client.set(key, value, ex=ex, px=px, nx=nx, xx=xx)  # type: ignore[misc]
        return bool(result) if result is not None else None

    async def delete(self, *keys: str) -> int:
        """Delete one or more keys."""
        client = self._ensure_connected()
        result = await client.delete(*keys)  # type: ignore[misc]
        return int(result)

    async def exists(self, *keys: str) -> int:
        """Check if keys exist."""
        client = self._ensure_connected()
        result = await client.exists(*keys)  # type: ignore[misc]
        return int(result)

    async def expire(self, key: str, seconds: int) -> bool:
        """Set expiration on a key."""
        client = self._ensure_connected()
        result = await client.expire(key, seconds)  # type: ignore[misc]
        return bool(result)

    async def ttl(self, key: str) -> int:
        """Get time to live for a key."""
        client = self._ensure_connected()
        result = await client.ttl(key)  # type: ignore[misc]
        return int(result)

    async def incr(self, key: str, amount: int = 1) -> int:
        """Increment value by amount."""
        client = self._ensure_connected()
        result = await client.incrby(key, amount)  # type: ignore[misc]
        return int(result)

    async def decr(self, key: str, amount: int = 1) -> int:
        """Decrement value by amount."""
        client = self._ensure_connected()
        result = await client.decrby(key, amount)  # type: ignore[misc]
        return int(result)

    async def hget(self, name: str, key: str) -> Optional[str]:
        """Get hash field value."""
        client = self._ensure_connected()
        result = await client.hget(name, key)  # type: ignore[misc]
        if result is None:
            return None
        return result.decode() if isinstance(result, bytes) else str(result)

    async def hset(
        self,
        name: str,
        key: Optional[str] = None,
        value: Optional[str] = None,
        mapping: Optional[Dict[str, Any]] = None,
    ) -> int:
        """Set hash field value."""
        client = self._ensure_connected()
        if mapping is not None:
            result = await client.hset(name, mapping=mapping)  # type: ignore[misc]
        elif key is not None and value is not None:
            result = await client.hset(name, key, value)  # type: ignore[misc]
        else:
            raise ValueError("Either mapping or both key and value must be provided")
        return int(result)

    async def hgetall(self, name: str) -> Dict[str, str]:
        """Get all fields and values in a hash."""
        client = self._ensure_connected()
        result = await client.hgetall(name)  # type: ignore[misc]
        return {
            (k.decode() if isinstance(k, bytes) else str(k)): (
                v.decode() if isinstance(v, bytes) else str(v)
            )
            for k, v in result.items()
        }

    async def hdel(self, name: str, *keys: str) -> int:
        """Delete hash fields."""
        client = self._ensure_connected()
        result = await client.hdel(name, *keys)  # type: ignore[misc]
        return int(result)

    async def lpush(self, name: str, *values: Any) -> int:
        """Prepend values to a list."""
        client = self._ensure_connected()
        result = await client.lpush(name, *values)  # type: ignore[misc]
        return int(result)

    async def rpush(self, name: str, *values: Any) -> int:
        """Append values to a list."""
        client = self._ensure_connected()
        result = await client.rpush(name, *values)  # type: ignore[misc]
        return int(result)

    async def lpop(
        self,
        name: str,
        count: Optional[int] = None,
    ) -> Optional[Union[str, List[str]]]:
        """Remove and return the first element(s) of a list."""
        client = self._ensure_connected()
        result = await client.lpop(name, count)  # type: ignore[misc]
        if result is None:
            return None
        if isinstance(result, list):
            return [v.decode() if isinstance(v, bytes) else str(v) for v in result]
        return result.decode() if isinstance(result, bytes) else str(result)

    async def rpop(
        self,
        name: str,
        count: Optional[int] = None,
    ) -> Optional[Union[str, List[str]]]:
        """Remove and return the last element(s) of a list."""
        client = self._ensure_connected()
        result = await client.rpop(name, count)  # type: ignore[misc]
        if result is None:
            return None
        if isinstance(result, list):
            return [v.decode() if isinstance(v, bytes) else str(v) for v in result]
        return result.decode() if isinstance(result, bytes) else str(result)

    async def lrange(self, name: str, start: int, end: int) -> List[str]:
        """Get a range of elements from a list."""
        client = self._ensure_connected()
        result = await client.lrange(name, start, end)  # type: ignore[misc]
        return [v.decode() if isinstance(v, bytes) else str(v) for v in result]

    async def sadd(self, name: str, *values: Any) -> int:
        """Add members to a set."""
        client = self._ensure_connected()
        result = await client.sadd(name, *values)  # type: ignore[misc]
        return int(result)

    async def srem(self, name: str, *values: Any) -> int:
        """Remove members from a set."""
        client = self._ensure_connected()
        result = await client.srem(name, *values)  # type: ignore[misc]
        return int(result)

    async def smembers(self, name: str) -> Set[str]:
        """Get all members of a set."""
        client = self._ensure_connected()
        result = await client.smembers(name)  # type: ignore[misc]
        return {v.decode() if isinstance(v, bytes) else str(v) for v in result}

    async def sismember(self, name: str, value: Any) -> bool:
        """Check if value is a member of a set."""
        client = self._ensure_connected()
        result = await client.sismember(name, value)  # type: ignore[misc]
        return bool(result)

    async def get_json(self, key: str) -> Optional[Any]:
        """Get JSON value by key."""
        value = await self.get(key)
        if value is None:
            return None
        return json.loads(value)

    async def set_json(
        self,
        key: str,
        value: Any,
        ex: Optional[int] = None,
    ) -> Optional[bool]:
        """Set JSON value with optional expiration."""
        return await self.set(key, json.dumps(value, default=str), ex=ex)

    async def publish(self, channel: str, message: str) -> int:
        """Publish a message to a channel."""
        client = self._ensure_connected()
        result = await client.publish(channel, message)  # type: ignore[misc]
        return int(result)

    def pubsub(self) -> Any:
        """Get a PubSub instance."""
        client = self._ensure_connected()
        return client.pubsub()


redis_client = RedisClient()
