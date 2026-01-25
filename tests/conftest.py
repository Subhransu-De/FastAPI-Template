import sys

import pytest
from pydantic_settings import BaseSettings, SettingsConfigDict

if sys.platform == "win32":
    import asyncio

    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())


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
