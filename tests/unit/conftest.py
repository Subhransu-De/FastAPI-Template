from collections.abc import AsyncGenerator

import pytest
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine
from sqlalchemy.pool import StaticPool

from app.database import SessionMaker, create_sessionmaker
from app.model import Base


@pytest.fixture
async def sqlite_engine() -> AsyncGenerator[AsyncEngine]:
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        poolclass=StaticPool,
        connect_args={"check_same_thread": False},
    )
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    try:
        yield engine
    finally:
        await engine.dispose()


@pytest.fixture
def sqlite_sessionmaker(sqlite_engine: AsyncEngine) -> SessionMaker:
    return create_sessionmaker(sqlite_engine)
