from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine

from app.settings import db_settings

_engine: AsyncEngine | None = None


def get_engine() -> AsyncEngine:
    global _engine
    if _engine is None:
        _engine = create_async_engine(
            db_settings.url,
            pool_size=db_settings.pool_size,
            max_overflow=db_settings.max_overflow,
            echo=db_settings.echo,
            pool_pre_ping=db_settings.pool_pre_ping,
        )
    return _engine
