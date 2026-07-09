from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from app.exceptions import NoEntityFoundError
from app.io.entity import EntityCreate, EntityOrderBy, EntityUpdate, OrderDirection
from app.model.entity import Entity
from app.service import get_entity_service
from app.service.entity import EntityService

pytestmark = pytest.mark.unit


@pytest.fixture
def session() -> AsyncMock:
    return AsyncMock()


@pytest.fixture
def repository() -> AsyncMock:
    return AsyncMock()


@pytest.fixture
def service(session: AsyncMock, repository: AsyncMock) -> EntityService:
    return EntityService(repository)


def test_get_entity_service_returns_bound_session(session: AsyncMock) -> None:
    service = get_entity_service(session)

    assert isinstance(service, EntityService)
    assert service.repo.session is session


async def test_create_builds_entity_and_saves(
    service: EntityService,
    session: AsyncMock,
    repository: AsyncMock,
) -> None:
    repository.save.side_effect = lambda entity: entity

    result = await service.create(EntityCreate(name="Created", description="Desc"))

    repository.save.assert_awaited_once()
    saved_entity = repository.save.await_args.args[0]
    assert isinstance(saved_entity, Entity)
    assert saved_entity.name == "Created"
    assert saved_entity.description == "Desc"
    session.commit.assert_not_awaited()
    assert result is saved_entity


async def test_get_by_id_returns_repository_result(
    service: EntityService,
    repository: AsyncMock,
) -> None:
    entity_id = uuid4()
    entity = Entity(id=entity_id, name="Fetched", description=None)
    repository.find_by_id.return_value = entity

    result = await service.get_by_id(entity_id)

    repository.find_by_id.assert_awaited_once_with(entity_id)
    assert result is entity


async def test_get_all_passes_pagination_and_default_order(
    service: EntityService,
    repository: AsyncMock,
) -> None:
    repository.find_all_paginated.return_value = []

    result = await service.get_all(offset=10, limit=5)

    repository.find_all_paginated.assert_awaited_once()
    call = repository.find_all_paginated.await_args
    assert call.kwargs["offset"] == 10
    assert call.kwargs["limit"] == 5
    assert str(call.kwargs["order_by"]) == "entities.created_at ASC"
    assert result == []


@pytest.mark.parametrize("order_by", list(EntityOrderBy))
@pytest.mark.parametrize("direction", list(OrderDirection))
async def test_get_all_allows_one_safe_entity_order_column(
    service: EntityService,
    repository: AsyncMock,
    order_by: EntityOrderBy,
    direction: OrderDirection,
) -> None:
    repository.find_all_paginated.return_value = []

    await service.get_all(order_by=order_by, order_direction=direction)

    clause = repository.find_all_paginated.await_args.kwargs["order_by"]
    assert str(clause) == f"entities.{order_by.value} {direction.value.upper()}"


async def test_update_raises_not_found_when_entity_does_not_exist(
    service: EntityService,
    session: AsyncMock,
    repository: AsyncMock,
) -> None:
    entity_id = uuid4()
    repository.find_by_id.return_value = None

    with pytest.raises(NoEntityFoundError):
        await service.update(entity_id, EntityUpdate(name="Updated"))

    repository.update.assert_not_awaited()
    session.commit.assert_not_awaited()


async def test_update_applies_payload_fields(
    service: EntityService,
    session: AsyncMock,
    repository: AsyncMock,
) -> None:
    entity_id = uuid4()
    entity = Entity(id=entity_id, name="Original", description="Original desc")
    repository.find_by_id.return_value = entity
    repository.update.side_effect = lambda updated: updated

    result = await service.update(
        entity_id,
        EntityUpdate(name="Updated", description="New desc"),
    )

    repository.update.assert_awaited_once_with(entity)
    session.commit.assert_not_awaited()
    assert result is entity
    assert entity.name == "Updated"
    assert entity.description == "New desc"


async def test_update_can_clear_nullable_fields(
    service: EntityService,
    repository: AsyncMock,
) -> None:
    entity_id = uuid4()
    entity = Entity(id=entity_id, name="Original", description="Original desc")
    repository.find_by_id.return_value = entity
    repository.update.side_effect = lambda updated: updated

    result = await service.update(
        entity_id, EntityUpdate(name="Original", description=None)
    )

    repository.update.assert_awaited_once_with(entity)
    assert result is entity
    assert entity.name == "Original"
    assert entity.description is None


async def test_delete_deletes_by_id(
    service: EntityService,
    session: AsyncMock,
    repository: AsyncMock,
) -> None:
    entity_id = uuid4()
    repository.delete_by_id.return_value = True

    await service.delete(entity_id)

    repository.delete_by_id.assert_awaited_once_with(entity_id)
    session.commit.assert_not_awaited()


async def test_get_by_id_raises_not_found_when_missing(
    service: EntityService,
    repository: AsyncMock,
) -> None:
    entity_id = uuid4()
    repository.find_by_id.return_value = None

    with pytest.raises(NoEntityFoundError):
        await service.get_by_id(entity_id)


async def test_delete_raises_not_found_when_missing(
    service: EntityService,
    repository: AsyncMock,
) -> None:
    entity_id = uuid4()
    repository.delete_by_id.return_value = False

    with pytest.raises(NoEntityFoundError):
        await service.delete(entity_id)
