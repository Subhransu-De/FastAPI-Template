import pytest
from fastapi import Request
from sqlalchemy import select

from app.database import (
    SessionMaker,
    get_probe_sessionmaker,
    get_session,
    get_sessionmaker,
)
from app.exceptions import MissingLifespanStateError
from app.model.entity import Entity

pytestmark = pytest.mark.unit


def _request_with_state(**state: object) -> Request:
    return Request({"type": "http", "state": state})


async def test_get_sessionmaker_reads_lifespan_state(
    sqlite_sessionmaker: SessionMaker,
) -> None:
    request = _request_with_state(sessionmaker=sqlite_sessionmaker)

    assert get_sessionmaker(request) is sqlite_sessionmaker


def test_get_sessionmaker_fails_when_lifespan_did_not_run() -> None:
    request = _request_with_state()

    with pytest.raises(MissingLifespanStateError, match="sessionmaker"):
        get_sessionmaker(request)


def test_get_sessionmaker_rejects_unexpected_state_values() -> None:
    request = _request_with_state(sessionmaker=object())

    with pytest.raises(MissingLifespanStateError, match="sessionmaker"):
        get_sessionmaker(request)


async def _count_entities(sessionmaker: SessionMaker) -> int:
    async with sessionmaker() as session:
        result = await session.execute(select(Entity))
        return len(result.scalars().all())


async def test_get_session_commits_when_the_request_succeeds(
    sqlite_sessionmaker: SessionMaker,
) -> None:
    generator = get_session(sqlite_sessionmaker)

    session = await anext(generator)
    session.add(Entity(name="Committed", description=None))
    with pytest.raises(StopAsyncIteration):
        await anext(generator)

    assert await _count_entities(sqlite_sessionmaker) == 1


async def test_get_session_rolls_back_when_the_request_fails(
    sqlite_sessionmaker: SessionMaker,
) -> None:
    generator = get_session(sqlite_sessionmaker)

    session = await anext(generator)
    session.add(Entity(name="Rolled back", description=None))
    failure = RuntimeError("boom")

    with pytest.raises(RuntimeError, match="boom"):
        await generator.athrow(failure)

    assert await _count_entities(sqlite_sessionmaker) == 0


async def test_get_probe_sessionmaker_reads_its_own_lifespan_state(
    sqlite_sessionmaker: SessionMaker,
) -> None:
    request = _request_with_state(probe_sessionmaker=sqlite_sessionmaker)

    assert get_probe_sessionmaker(request) is sqlite_sessionmaker


async def test_get_probe_sessionmaker_does_not_fall_back_to_the_request_pool(
    sqlite_sessionmaker: SessionMaker,
) -> None:
    request = _request_with_state(sessionmaker=sqlite_sessionmaker)

    with pytest.raises(MissingLifespanStateError, match="probe_sessionmaker"):
        get_probe_sessionmaker(request)
