from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from app.exceptions import NoEntityFoundError
from app.io.entity import EntityCreate, EntityUpdate
from app.model.entity import Entity
from app.routes.entity import (
    create_entity,
    delete_entity,
    get_entity,
    list_entities,
    update_entity,
)

pytestmark = pytest.mark.unit


def make_entity(name: str = "Entity", description: str | None = None) -> Entity:
    now = datetime.now(UTC)
    return Entity(
        id=uuid4(),
        name=name,
        description=description,
        created_at=now,
        updated_at=now,
    )


@pytest.fixture
def service():
    return SimpleNamespace(
        create=AsyncMock(),
        get_by_id=AsyncMock(),
        get_all=AsyncMock(),
        update=AsyncMock(),
        delete=AsyncMock(),
    )


async def test_create_entity_returns_response(service):
    entity = make_entity(name="Created", description="Created desc")
    service.create.return_value = entity

    response = await create_entity(
        EntityCreate(name="Created", description="Created desc"),
        service,
    )

    service.create.assert_awaited_once()
    assert response.id == entity.id
    assert response.name == "Created"
    assert response.description == "Created desc"


async def test_get_entity_returns_response(service):
    entity = make_entity(name="Fetched", description="Fetched desc")
    service.get_by_id.return_value = entity

    response = await get_entity(entity.id, service)

    service.get_by_id.assert_awaited_once_with(entity.id)
    assert response.id == entity.id
    assert response.name == "Fetched"


async def test_get_entity_raises_not_found(service):
    entity_id = uuid4()
    service.get_by_id.side_effect = NoEntityFoundError(entity_id)

    with pytest.raises(NoEntityFoundError):
        await get_entity(entity_id, service)


async def test_list_entities_returns_responses(service):
    entities = [
        make_entity(name="Entity A", description="Desc A"),
        make_entity(name="Entity B", description="Desc B"),
    ]
    service.get_all.return_value = entities

    response = await list_entities(service, offset=5, limit=10)

    service.get_all.assert_awaited_once_with(offset=5, limit=10)
    assert [item.name for item in response] == ["Entity A", "Entity B"]


async def test_update_entity_returns_response(service):
    entity = make_entity(name="Updated", description="Updated desc")
    entity_id = uuid4()
    payload = EntityUpdate(name="Updated", description="Updated desc")
    service.update.return_value = entity

    response = await update_entity(entity_id, payload, service)

    service.update.assert_awaited_once_with(entity_id, payload)
    assert response.id == entity.id
    assert response.description == "Updated desc"


async def test_update_entity_raises_not_found(service):
    entity_id = uuid4()
    payload = EntityUpdate(name="Updated")
    service.update.side_effect = NoEntityFoundError(entity_id)

    with pytest.raises(NoEntityFoundError):
        await update_entity(entity_id, payload, service)


async def test_delete_entity_calls_service(service):
    entity_id = uuid4()

    await delete_entity(entity_id, service)

    service.delete.assert_awaited_once_with(entity_id)
