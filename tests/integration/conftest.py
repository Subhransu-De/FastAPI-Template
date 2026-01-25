import importlib
import os
from typing import AsyncGenerator, Generator

import pytest
from alembic import command
from alembic.config import Config
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy import inspect, text
from sqlalchemy.ext.asyncio import AsyncSession, AsyncEngine
from testcontainers.core.container import Reaper
from testcontainers.postgres import PostgresContainer


@pytest.fixture(scope="session", autouse=True)
def reaper_cleanup() -> Generator[None, None, None]:
    yield
    Reaper.delete_instance()


@pytest.fixture(scope="session")
def database_url(reaper_cleanup: None) -> Generator[str, None, None]:
    previous = os.environ.get("DATABASE_URL")
    container = PostgresContainer("postgres:16")
    container.start()
    url = container.get_connection_url()
    async_url = url.replace("postgresql://", "postgresql+psycopg://", 1)
    os.environ["DATABASE_URL"] = async_url
    try:
        yield async_url
    finally:
        container.stop()
        if previous is None:
            os.environ.pop("DATABASE_URL", None)
        else:
            os.environ["DATABASE_URL"] = previous


@pytest.fixture(scope="session")
def migrated_db(database_url: str) -> None:
    alembic_cfg = Config("alembic.ini")
    alembic_cfg.set_main_option("script_location", "alembic")
    command.upgrade(alembic_cfg, "head")


@pytest.fixture(scope="session")
def app_instance(
    database_url: str, migrated_db: None
) -> Generator[FastAPI, None, None]:
    module = importlib.import_module("app.main")
    app = module.app
    from app.database import get_session
    from app.database.session import AsyncSessionLocal

    async def override_get_session() -> AsyncGenerator[AsyncSession, None]:
        async with AsyncSessionLocal() as session:
            try:
                yield session
            except Exception:
                await session.rollback()
                raise

    app.dependency_overrides[get_session] = override_get_session
    try:
        yield app
    finally:
        app.dependency_overrides = {}


@pytest.fixture(scope="session")
def engine(database_url: str) -> AsyncEngine:
    from app.database.engine import engine

    return engine


@pytest.fixture(scope="session", autouse=True)
def dispose_engine(engine: AsyncEngine) -> Generator[None, None, None]:
    yield
    engine.sync_engine.dispose()


@pytest.fixture(autouse=True)
async def cleanup_db(engine: AsyncEngine) -> AsyncGenerator[None, None]:
    yield
    async with engine.begin() as conn:

        def get_tables(sync_conn):
            inspector = inspect(sync_conn)
            return inspector.get_table_names()

        tables = await conn.run_sync(get_tables)
        tables = [table for table in tables if table != "alembic_version"]
        if tables:
            quoted = ", ".join(f'"{table}"' for table in tables)
            await conn.execute(
                text(f"TRUNCATE TABLE {quoted} RESTART IDENTITY CASCADE")
            )


@pytest.fixture
async def client(app_instance: FastAPI) -> AsyncGenerator[AsyncClient, None]:
    transport = ASGITransport(app=app_instance)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client
