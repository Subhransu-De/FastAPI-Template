from unittest.mock import AsyncMock, Mock

import pytest
from sqlalchemy.ext.asyncio import AsyncSession


@pytest.fixture
def mock_session() -> AsyncMock:
    session = AsyncMock(spec=AsyncSession)
    session.commit = AsyncMock()
    session.rollback = AsyncMock()
    session.flush = AsyncMock()
    session.refresh = AsyncMock()
    session.get = AsyncMock()
    session.execute = AsyncMock()
    session.add = Mock()
    session.add_all = Mock()
    session.merge = AsyncMock()
    return session


@pytest.fixture
def mock_entity_repository() -> AsyncMock:
    repo = AsyncMock()
    repo.save = AsyncMock()
    repo.find_by_id = AsyncMock()
    repo.find_all_paginated = AsyncMock()
    repo.update = AsyncMock()
    repo.delete_by_id = AsyncMock()
    repo.exists_by_id = AsyncMock()
    return repo
