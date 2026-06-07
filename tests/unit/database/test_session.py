from unittest.mock import AsyncMock, Mock

import pytest

import app.database.session as session_module

pytestmark = pytest.mark.unit


class DummySessionContext:
    def __init__(self, session):
        self.session = session

    async def __aenter__(self):
        return self.session

    async def __aexit__(self, exc_type, exc, tb):
        return False


def test_session_maker_proxy_initializes_once(monkeypatch):
    proxy = session_module._SessionMakerProxy()
    session_factory = Mock(side_effect=["session-1", "session-2"])
    async_sessionmaker = Mock(return_value=session_factory)
    get_engine = Mock(return_value="engine")

    monkeypatch.setattr(session_module, "async_sessionmaker", async_sessionmaker)
    monkeypatch.setattr(session_module, "get_engine", get_engine)

    first = proxy()
    second = proxy()

    get_engine.assert_called_once_with()
    async_sessionmaker.assert_called_once_with(
        bind="engine",
        expire_on_commit=False,
        autocommit=False,
        autoflush=False,
    )
    assert session_factory.call_count == 2
    assert first == "session-1"
    assert second == "session-2"


async def test_get_session_yields_session(monkeypatch):
    session = AsyncMock()
    session_factory = Mock(return_value=DummySessionContext(session))

    monkeypatch.setattr(session_module, "AsyncSessionLocal", session_factory)

    generator = session_module.get_session()

    yielded = await anext(generator)
    assert yielded is session

    with pytest.raises(StopAsyncIteration):
        await anext(generator)

    session_factory.assert_called_once_with()
    session.commit.assert_awaited_once_with()
    session.rollback.assert_not_awaited()


async def test_get_session_rolls_back_on_error(monkeypatch):
    session = AsyncMock()
    session_factory = Mock(return_value=DummySessionContext(session))

    monkeypatch.setattr(session_module, "AsyncSessionLocal", session_factory)

    generator = session_module.get_session()

    yielded = await anext(generator)
    assert yielded is session

    with pytest.raises(RuntimeError, match="boom"):
        await generator.athrow(RuntimeError("boom"))

    session.rollback.assert_awaited_once_with()
