from contextvars import ContextVar
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import settings
from app.core.singleton import Singleton

_session_ctx: ContextVar[AsyncSession] = ContextVar("db_session")


def get_session() -> AsyncSession:
    try:
        return _session_ctx.get()
    except LookupError:
        raise RuntimeError("No session in context. Is the middleware configured?")


class Database(Singleton):
    def __init__(self) -> None:
        self._initialized = False
        self._engine = None
        self._session_factory = None

    async def connect(self, db_url: str = None) -> None:
        if self._initialized:
            return
        url = db_url or settings.DATABASE_URL
        self._engine = create_async_engine(url, echo=settings.DEBUG)
        self._session_factory = async_sessionmaker(
            bind=self._engine,
            class_=AsyncSession,
            expire_on_commit=False,
        )
        self._initialized = True

    async def disconnect(self) -> None:
        if self._engine:
            await self._engine.dispose()
            self._initialized = False

    @asynccontextmanager
    async def session_context(self) -> AsyncGenerator[AsyncSession, None]:
        async with self._session_factory() as session:
            token = _session_ctx.set(session)
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise
            finally:
                _session_ctx.reset(token)


db = Database()
