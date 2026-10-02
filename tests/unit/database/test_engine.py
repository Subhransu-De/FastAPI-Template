import pytest
from sqlalchemy.pool import QueuePool

from app.database import create_engine, create_probe_engine
from app.database.engine import PROBE_POOL_TIMEOUT_SECONDS
from app.settings import DatabaseSettings

pytestmark = pytest.mark.unit


async def test_create_engine_applies_database_settings() -> None:
    settings = DatabaseSettings(
        _env_file=None,
        url="postgresql+psycopg://user:pass@localhost:5432/test",
        pool_size=7,
        max_overflow=3,
        echo=True,
        pool_pre_ping=False,
    )

    engine = create_engine(settings)
    try:
        pool = engine.pool
        assert isinstance(pool, QueuePool)
        assert engine.url.render_as_string(hide_password=False) == settings.url
        assert pool.size() == 7
        assert pool._max_overflow == 3
        assert engine.echo is True
        assert pool._pre_ping is False
    finally:
        await engine.dispose()


async def test_probe_engine_is_capped_at_one_connection() -> None:
    settings = DatabaseSettings(
        _env_file=None,
        url="postgresql+psycopg://user:pass@localhost:5432/test",
        pool_size=20,
        max_overflow=10,
    )

    engine = create_probe_engine(settings)
    try:
        pool = engine.pool
        assert isinstance(pool, QueuePool)
        assert pool.size() == 1
        assert pool._max_overflow == 0
        assert pool._timeout == PROBE_POOL_TIMEOUT_SECONDS
    finally:
        await engine.dispose()
