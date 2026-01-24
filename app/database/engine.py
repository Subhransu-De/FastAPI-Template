from sqlalchemy.ext.asyncio import create_async_engine

from app.settings import settings

engine = create_async_engine(
    settings.database_url,
    pool_size=settings.database_pool_size,
    max_overflow=settings.database_max_overflow,
    echo=settings.database_echo,
    pool_pre_ping=settings.database_pool_pre_ping,
)
