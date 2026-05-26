from uuid import uuid4

import pytest

from app.io.entity import EntityCreate, EntityUpdate
from app.model.entity import Entity
from app.service.entity import EntityService, get_entity_service

pytestmark = pytest.mark.unit


@pytest.fixture(autouse=True)
def _mock_get_session(monkeypatch):
    async def _dummy_get_session():
        yield None

    monkeypatch.setattr("app.database.get_session", _dummy_get_session)


class TestEntityService:
    @pytest.fixture
    def service(self, mock_session, mock_entity_repository):
        svc = EntityService(mock_session)
        svc.repo = mock_entity_repository
        return svc

    async def test_create_entity(self, service, mock_session, mock_entity_repository):
        entity = Entity(id=uuid4(), name="Test", description="Desc")
        mock_entity_repository.save.return_value = entity

        result = await service.create(EntityCreate(name="Test", description="Desc"))

        mock_entity_repository.save.assert_called_once()
        mock_session.commit.assert_called_once()
        assert result.name == "Test"

    async def test_get_by_id_returns_entity(self, service, mock_entity_repository):
        entity_id = uuid4()
        entity = Entity(id=entity_id, name="Test", description=None)
        mock_entity_repository.find_by_id.return_value = entity

        result = await service.get_by_id(entity_id)

        mock_entity_repository.find_by_id.assert_called_once_with(entity_id)
        assert result == entity

    async def test_get_by_id_returns_none(self, service, mock_entity_repository):
        entity_id = uuid4()
        mock_entity_repository.find_by_id.return_value = None

        result = await service.get_by_id(entity_id)

        assert result is None

    async def test_update_nonexistent_returns_none(
        self, service, mock_session, mock_entity_repository
    ):
        entity_id = uuid4()
        mock_entity_repository.find_by_id.return_value = None

        result = await service.update(entity_id, EntityUpdate(name="Updated"))

        mock_session.commit.assert_not_called()
        assert result is None

    async def test_update_entity(self, service, mock_session, mock_entity_repository):
        entity_id = uuid4()
        entity = Entity(id=entity_id, name="Old", description=None)
        updated_entity = Entity(id=entity_id, name="New", description=None)
        mock_entity_repository.find_by_id.return_value = entity
        mock_entity_repository.update.return_value = updated_entity

        result = await service.update(entity_id, EntityUpdate(name="New"))

        mock_entity_repository.update.assert_called_once()
        mock_session.commit.assert_called_once()
        assert result.name == "New"

    async def test_update_entity_description_only(
        self, service, mock_session, mock_entity_repository
    ):
        entity_id = uuid4()
        entity = Entity(id=entity_id, name="Old", description="Old description")
        updated_entity = Entity(
            id=entity_id,
            name="Old",
            description="New description",
        )
        mock_entity_repository.find_by_id.return_value = entity
        mock_entity_repository.update.return_value = updated_entity

        result = await service.update(
            entity_id,
            EntityUpdate(description="New description"),
        )

        mock_entity_repository.update.assert_called_once_with(entity)
        mock_session.commit.assert_called_once()
        assert entity.name == "Old"
        assert entity.description == "New description"
        assert result.description == "New description"

    async def test_delete_calls_commit(
        self, service, mock_session, mock_entity_repository
    ):
        entity_id = uuid4()

        await service.delete(entity_id)

        mock_entity_repository.delete_by_id.assert_called_once_with(entity_id)
        mock_session.commit.assert_called_once()

    async def test_get_all_paginated(self, service, mock_entity_repository):
        entities = [
            Entity(id=uuid4(), name=f"Entity {i}", description=None) for i in range(3)
        ]
        mock_entity_repository.find_all_paginated.return_value = entities

        result = await service.get_all(offset=0, limit=10)

        mock_entity_repository.find_all_paginated.assert_called_once_with(
            offset=0, limit=10
        )
        assert len(result) == 3

    async def test_get_entity_service_returns_bound_session(
        self, mock_session, monkeypatch
    ):
        repository = object()

        def repository_factory(_session):
            return repository

        monkeypatch.setattr(
            "app.service.entity.EntityRepository",
            repository_factory,
        )

        service = get_entity_service(mock_session)

        assert isinstance(service, EntityService)
        assert service.session is mock_session
        assert service.repo is repository
