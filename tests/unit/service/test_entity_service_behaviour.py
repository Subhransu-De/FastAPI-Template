from collections.abc import Sequence
from uuid import UUID, uuid4

import pytest

from app.exceptions import NoEntityFoundError
from app.io.entity import EntityCreate, EntityOrderBy, EntityUpdate, OrderDirection
from app.model.entity import Entity
from app.repository import Ordering
from app.service.entity import EntityService

pytestmark = pytest.mark.unit


class InMemoryEntityStore:
    def __init__(self) -> None:
        self.entities: dict[UUID, Entity] = {}
        self.page_requests: list[tuple[int, int, Ordering | None]] = []

    async def save(self, entity: Entity) -> Entity:
        if entity.id is None:
            entity.id = uuid4()
        self.entities[entity.id] = entity
        return entity

    async def find_by_id(self, entity_id: UUID) -> Entity | None:
        return self.entities.get(entity_id)

    async def find_all_paginated(
        self,
        offset: int = 0,
        limit: int = 25,
        ordering: Ordering | None = None,
    ) -> Sequence[Entity]:
        self.page_requests.append((offset, limit, ordering))
        return list(self.entities.values())[offset : offset + limit]

    async def update(self, entity: Entity) -> Entity:
        self.entities[entity.id] = entity
        return entity

    async def delete_by_id(self, entity_id: UUID) -> bool:
        return self.entities.pop(entity_id, None) is not None


@pytest.fixture
def store() -> InMemoryEntityStore:
    return InMemoryEntityStore()


@pytest.fixture
def service(store: InMemoryEntityStore) -> EntityService:
    return EntityService(store)


async def test_create_persists_a_new_entity(
    service: EntityService,
    store: InMemoryEntityStore,
) -> None:
    created = await service.create(EntityCreate(name="Created", description="Desc"))

    assert created.name == "Created"
    assert created.description == "Desc"
    assert store.entities[created.id] is created


async def test_get_by_id_returns_the_stored_entity(
    service: EntityService,
    store: InMemoryEntityStore,
) -> None:
    entity = await store.save(Entity(name="Fetched", description=None))

    assert await service.get_by_id(entity.id) is entity


async def test_get_by_id_raises_not_found_when_missing(service: EntityService) -> None:
    with pytest.raises(NoEntityFoundError):
        await service.get_by_id(uuid4())


async def test_get_all_passes_pagination_and_default_ordering(
    service: EntityService,
    store: InMemoryEntityStore,
) -> None:
    result = await service.get_all(offset=10, limit=5)

    assert result == []
    assert store.page_requests == [
        (10, 5, Ordering(column=Entity.created_at, descending=False))
    ]


@pytest.mark.parametrize("order_by", list(EntityOrderBy))
@pytest.mark.parametrize("direction", list(OrderDirection))
async def test_get_all_orders_by_one_known_column(
    service: EntityService,
    store: InMemoryEntityStore,
    order_by: EntityOrderBy,
    direction: OrderDirection,
) -> None:
    await service.get_all(order_by=order_by, order_direction=direction)

    (_, _, ordering) = store.page_requests[0]
    assert ordering is not None
    assert ordering.column.key == order_by.value
    assert ordering.descending is (direction is OrderDirection.DESC)


async def test_update_replaces_every_writable_field(
    service: EntityService,
    store: InMemoryEntityStore,
) -> None:
    entity = await store.save(Entity(name="Original", description="Original desc"))

    result = await service.update(entity.id, EntityUpdate(name="Updated"))

    assert result is entity
    assert entity.name == "Updated"
    assert entity.description is None


async def test_update_raises_not_found_when_entity_does_not_exist(
    service: EntityService,
) -> None:
    with pytest.raises(NoEntityFoundError):
        await service.update(uuid4(), EntityUpdate(name="Updated"))


async def test_delete_removes_the_entity(
    service: EntityService,
    store: InMemoryEntityStore,
) -> None:
    entity = await store.save(Entity(name="Delete me", description=None))

    await service.delete(entity.id)

    assert entity.id not in store.entities


async def test_delete_raises_not_found_when_missing(service: EntityService) -> None:
    with pytest.raises(NoEntityFoundError):
        await service.delete(uuid4())
