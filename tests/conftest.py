import sys
from collections.abc import AsyncGenerator, Iterator

import httpx
import pytest
import pytest_asyncio
from alembic.config import Config
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from testcontainers.postgres import PostgresContainer

from alembic import command
from app.model import Base

if sys.platform == "win32":
    import asyncio

    # Use the selector loop on Windows for async DB and HTTP client test stability.
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

DOCKER_COMPOSE_DATABASE_URL = (
    "postgresql+psycopg://postgres:postgres@db:5432/fastapi_db"
)


class TestSettings(BaseSettings):
    model_config = SettingsConfigDict()

    app_name: str = "FastAPI Template Test"
    port: int = 8000

    database_url: str = "sqlite+aiosqlite:///:memory:"
    database_pool_size: int = 5
    database_max_overflow: int = 10
    database_echo: bool = False
    database_pool_pre_ping: bool = True


@pytest.fixture
def test_settings() -> TestSettings:
    return TestSettings()


def assert_not_docker_compose_db(database_url: str) -> None:
    parsed = make_url(database_url)

    assert "@db:5432/fastapi_db" not in database_url
    assert parsed.host != "db"
    assert database_url != DOCKER_COMPOSE_DATABASE_URL


def normalize_testcontainers_url(database_url: str) -> str:
    parsed = make_url(database_url)
    if parsed.host == "localhost":
        parsed = parsed.set(host="127.0.0.1")
    return parsed.render_as_string(hide_password=False)


@pytest.fixture(scope="session")
def postgres_container() -> Iterator[PostgresContainer]:
    with PostgresContainer(
        image="postgres:18-alpine",
        username="postgres",
        password="postgres",  # noqa: S106
        dbname="fastapi_test",
        driver="psycopg",
    ) as container:
        database_url = normalize_testcontainers_url(container.get_connection_url())
        assert_not_docker_compose_db(database_url)
        yield container


@pytest.fixture(scope="session")
def test_postgres_url(postgres_container: PostgresContainer) -> str:
    database_url = normalize_testcontainers_url(postgres_container.get_connection_url())
    assert_not_docker_compose_db(database_url)

    cfg = Config("alembic.ini")
    cfg.set_main_option("script_location", "alembic")
    cfg.set_main_option("sqlalchemy.url", database_url)
    command.upgrade(cfg, "head")

    return database_url


@pytest_asyncio.fixture
async def integration_engine(test_postgres_url: str) -> AsyncGenerator[AsyncEngine]:
    assert_not_docker_compose_db(test_postgres_url)
    engine = create_async_engine(test_postgres_url, echo=False, pool_pre_ping=True)
    try:
        yield engine
    finally:
        await engine.dispose()


@pytest_asyncio.fixture
async def integration_sessionmaker(
    integration_engine: AsyncEngine,
) -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(
        bind=integration_engine,
        expire_on_commit=False,
        autocommit=False,
        autoflush=False,
    )


@pytest_asyncio.fixture
async def clean_integration_database(
    integration_engine: AsyncEngine,
) -> AsyncGenerator[None]:
    yield

    async with integration_engine.begin() as conn:
        for table in reversed(Base.metadata.sorted_tables):
            await conn.execute(table.delete())


@pytest_asyncio.fixture
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
        base_url="http://testserver",
    ) as client:
        yield client

    app.dependency_overrides.clear()
