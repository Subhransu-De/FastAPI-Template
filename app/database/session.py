from collections.abc import AsyncGenerator
from typing import Annotated

from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from app.exceptions import MissingLifespanStateError

SESSIONMAKER_STATE_KEY = "sessionmaker"
PROBE_SESSIONMAKER_STATE_KEY = "probe_sessionmaker"

type SessionMaker = async_sessionmaker[AsyncSession]


def create_sessionmaker(engine: AsyncEngine) -> SessionMaker:
    return async_sessionmaker(
        bind=engine,
        expire_on_commit=False,
        autocommit=False,
        autoflush=False,
    )


def get_sessionmaker(request: Request) -> SessionMaker:
    try:
        sessionmaker = request.state.sessionmaker
    except AttributeError as error:
        raise MissingLifespanStateError(SESSIONMAKER_STATE_KEY) from error
    if not isinstance(sessionmaker, async_sessionmaker):
        raise MissingLifespanStateError(SESSIONMAKER_STATE_KEY)
    return sessionmaker


def get_probe_sessionmaker(request: Request) -> SessionMaker:
    try:
        sessionmaker = request.state.probe_sessionmaker
    except AttributeError as error:
        raise MissingLifespanStateError(PROBE_SESSIONMAKER_STATE_KEY) from error
    if not isinstance(sessionmaker, async_sessionmaker):
        raise MissingLifespanStateError(PROBE_SESSIONMAKER_STATE_KEY)
    return sessionmaker


async def get_session(
    sessionmaker: Annotated[SessionMaker, Depends(get_sessionmaker)],
) -> AsyncGenerator[AsyncSession]:
    async with sessionmaker() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
