from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.database.engine import get_engine


class _SessionMakerProxy:
    def __init__(self) -> None:
        self._sessionmaker = None

    def __call__(self, *args, **kwargs):
        if self._sessionmaker is None:
            self._sessionmaker = async_sessionmaker(
                bind=get_engine(),
                expire_on_commit=False,
                autocommit=False,
                autoflush=False,
            )
        return self._sessionmaker(*args, **kwargs)


AsyncSessionLocal = _SessionMakerProxy()


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
