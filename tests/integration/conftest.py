import asyncio
import selectors
import sys
from collections.abc import AsyncGenerator, Iterator
from os import environ
from typing import Any

import httpx
import pytest
from alembic.config import Config
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from testcontainers.postgres import PostgresContainer

from alembic import command
from app.model import Base


class TestSettings(BaseSettings):
    model_config = SettingsConfigDict()

    app_name: str = "FastAPI Template Test"
    port: int = 8000

    database_url: str = "dummy://"
    database_pool_size: int = 5
    database_max_overflow: int = 10
    database_echo: bool = False
    database_pool_pre_ping: bool = True


@pytest.fixture
def test_settings() -> TestSettings:
    return TestSettings()


def selector_event_loop() -> asyncio.AbstractEventLoop:
    return asyncio.SelectorEventLoop(selectors.SelectSelector())


@pytest.fixture
def anyio_backend() -> str | tuple[str, dict[str, Any]]:
    if sys.platform == "win32":
        return "asyncio", {"loop_factory": selector_event_loop}
    return "asyncio"


@pytest.fixture(scope="session")
def postgres_container() -> Iterator[PostgresContainer]:
    with PostgresContainer(
        image="postgres:18-alpine",
        username="postgres",
        password=environ.get("INTEGRATION_TEST_CONTAINER_PASSWORD", "postgres"),
        dbname="fastapi_test",
        driver="psycopg",
    ) as container:
        yield container


@pytest.fixture(scope="session")
def test_postgres_url(postgres_container: PostgresContainer) -> str:
    database_url = postgres_container.get_connection_url(host="127.0.0.1")

    cfg = Config("alembic.ini")
    cfg.set_main_option("script_location", "alembic")
    cfg.set_main_option("sqlalchemy.url", database_url)
    command.upgrade(cfg, "head")

    return database_url


@pytest.fixture
async def integration_engine(test_postgres_url: str) -> AsyncGenerator[AsyncEngine]:
    engine = create_async_engine(test_postgres_url, echo=False, pool_pre_ping=True)
    try:
        yield engine
    finally:
        await engine.dispose()


@pytest.fixture
async def integration_sessionmaker(
    integration_engine: AsyncEngine,
) -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(
        bind=integration_engine,
        expire_on_commit=False,
        autocommit=False,
        autoflush=False,
    )


@pytest.fixture
async def clean_integration_database(
    integration_engine: AsyncEngine,
) -> AsyncGenerator[None]:
    yield

    async with integration_engine.begin() as conn:
        for table in reversed(Base.metadata.sorted_tables):
            await conn.execute(table.delete())


@pytest.fixture
async def app_client(
    integration_sessionmaker: async_sessionmaker[AsyncSession],
    clean_integration_database: None,
) -> AsyncGenerator[httpx.AsyncClient]:
    from app.database import session as session_module
    from app.main import app

    async def override_get_session() -> AsyncGenerator[AsyncSession]:
        async with integration_sessionmaker() as session:
            try:
                yield session
            except Exception:
                await session.rollback()
                raise

    app.dependency_overrides[session_module.get_session] = override_get_session

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(
        transport=transport,
        base_url="https://testserver",
    ) as client:
        yield client

    app.dependency_overrides.clear()
