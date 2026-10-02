from sqlalchemy.ext import asyncio as sqlalchemy_asyncio
from sqlalchemy.ext.asyncio import AsyncEngine

from app.settings import DatabaseSettings

PROBE_POOL_TIMEOUT_SECONDS = 1.0


def create_engine(settings: DatabaseSettings) -> AsyncEngine:
    return sqlalchemy_asyncio.create_async_engine(
        settings.url,
        pool_size=settings.pool_size,
        max_overflow=settings.max_overflow,
        echo=settings.echo,
        pool_pre_ping=settings.pool_pre_ping,
    )


def create_probe_engine(settings: DatabaseSettings) -> AsyncEngine:
    return sqlalchemy_asyncio.create_async_engine(
        settings.url,
        pool_size=1,
        max_overflow=0,
        pool_timeout=PROBE_POOL_TIMEOUT_SECONDS,
        pool_pre_ping=False,
    )
