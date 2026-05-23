from uuid import uuid4

import pytest

from app.model.entity import Entity
from app.repository.base import BaseRepository

pytestmark = pytest.mark.unit


class ScalarResultStub:
    def __init__(self, values):
        self.values = values

    def all(self):
        return self.values


class ResultStub:
    def __init__(self, values=None, scalar_value=None, rowcount=0):
        self.values = values or []
        self.scalar_value = scalar_value
        self.rowcount = rowcount

    def scalars(self):
        return ScalarResultStub(self.values)

    def scalar_one(self):
        return self.scalar_value


class TestBaseRepository:
    @pytest.fixture
    def repository(self, mock_session):
        return BaseRepository(Entity, mock_session)

    async def test_save_adds_flushes_refreshes_and_returns_entity(
        self, repository, mock_session
    ):
        entity = Entity(name="Test Entity", description="Test description")

        saved = await repository.save(entity)

        assert saved is entity
        mock_session.add.assert_called_once_with(entity)
        mock_session.flush.assert_awaited_once_with()
        mock_session.refresh.assert_awaited_once_with(entity)

    async def test_find_by_id_returns_session_get_result(self, repository, mock_session):
        entity_id = uuid4()
        entity = Entity(id=entity_id, name="Test Entity", description=None)
        mock_session.get.return_value = entity

        result = await repository.find_by_id(entity_id)

        assert result is entity
        mock_session.get.assert_awaited_once_with(Entity, entity_id)

    async def test_find_by_id_not_found(self, repository, mock_session):
        entity_id = uuid4()
        mock_session.get.return_value = None

        result = await repository.find_by_id(entity_id)

        assert result is None
        mock_session.get.assert_awaited_once_with(Entity, entity_id)

    async def test_find_all_returns_scalars(self, repository, mock_session):
        entities = [Entity(name="Entity 1", description=None)]
        mock_session.execute.return_value = ResultStub(values=entities)

        result = await repository.find_all()

        assert result == entities
        mock_session.execute.assert_awaited_once()

    async def test_find_all_empty(self, repository, mock_session):
        mock_session.execute.return_value = ResultStub(values=[])

        result = await repository.find_all()

        assert result == []
        mock_session.execute.assert_awaited_once()

    async def test_find_all_paginated(self, repository, mock_session):
        entities = [Entity(name="Entity 1", description=None)]
        mock_session.execute.return_value = ResultStub(values=entities)

        result = await repository.find_all_paginated(offset=2, limit=10)

        assert result == entities
        mock_session.execute.assert_awaited_once()

    async def test_find_all_paginated_with_order_by(self, repository, mock_session):
        entities = [Entity(name="Alpha", description=None)]
        mock_session.execute.return_value = ResultStub(values=entities)

        result = await repository.find_all_paginated(
            offset=0,
            limit=10,
            order_by=Entity.name.asc(),
        )

        assert result == entities
        mock_session.execute.assert_awaited_once()

    async def test_delete_by_id(self, repository, mock_session):
        entity_id = uuid4()
        mock_session.execute.return_value = ResultStub(rowcount=1)

        deleted = await repository.delete_by_id(entity_id)

        assert deleted is True
        mock_session.execute.assert_awaited_once()
        mock_session.flush.assert_awaited_once_with()

    async def test_delete_by_id_not_found(self, repository, mock_session):
        entity_id = uuid4()
        mock_session.execute.return_value = ResultStub(rowcount=0)

        deleted = await repository.delete_by_id(entity_id)

        assert deleted is False
        mock_session.execute.assert_awaited_once()
        mock_session.flush.assert_awaited_once_with()

    async def test_exists_by_id(self, repository, mock_session):
        entity_id = uuid4()
        mock_session.execute.return_value = ResultStub(scalar_value=1)

        assert await repository.exists_by_id(entity_id) is True
        mock_session.execute.assert_awaited_once()

    async def test_exists_by_id_returns_false_when_missing(self, repository, mock_session):
        entity_id = uuid4()
        mock_session.execute.return_value = ResultStub(scalar_value=0)

        assert await repository.exists_by_id(entity_id) is False
        mock_session.execute.assert_awaited_once()

    async def test_update(self, repository, mock_session):
        entity = Entity(name="Original", description=None)
        updated = Entity(id=entity.id, name="Updated", description=None)
        mock_session.merge.return_value = updated

        result = await repository.update(entity)

        assert result is updated
        mock_session.merge.assert_awaited_once_with(entity)
        mock_session.flush.assert_awaited_once_with()
        mock_session.refresh.assert_awaited_once_with(updated)

    async def test_find_by(self, repository, mock_session):
        entities = [Entity(name="Alpha", description="First")]
        mock_session.execute.return_value = ResultStub(values=entities)

        result = await repository.find_by(name="Alpha")

        assert result == entities
        mock_session.execute.assert_awaited_once()

    async def test_save_all(self, repository, mock_session):
        entities = [
            Entity(name="Batch 1", description=None),
            Entity(name="Batch 2", description=None),
        ]

        saved = await repository.save_all(entities)

        assert saved == entities
        mock_session.add_all.assert_called_once_with(entities)
        mock_session.flush.assert_awaited_once_with()
        assert mock_session.refresh.await_count == 2

    async def test_find_all_by_id(self, repository, mock_session):
        ids = [uuid4(), uuid4()]
        entities = [Entity(id=ids[0], name="E1", description=None)]
        mock_session.execute.return_value = ResultStub(values=entities)

        result = await repository.find_all_by_id(ids)

        assert result == entities
        mock_session.execute.assert_awaited_once()

    async def test_find_all_by_id_empty_list(self, repository, mock_session):
        result = await repository.find_all_by_id([])

        assert result == []
        mock_session.execute.assert_not_awaited()

    async def test_delete_all_by_id(self, repository, mock_session):
        mock_session.execute.return_value = ResultStub(rowcount=2)

        count = await repository.delete_all_by_id([uuid4(), uuid4()])

        assert count == 2
        mock_session.execute.assert_awaited_once()
        mock_session.flush.assert_awaited_once_with()

    async def test_delete_all_by_id_empty_list(self, repository, mock_session):
        count = await repository.delete_all_by_id([])

        assert count == 0
        mock_session.execute.assert_not_awaited()
        mock_session.flush.assert_not_awaited()
