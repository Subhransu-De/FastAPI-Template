from collections.abc import Mapping, Sequence
from typing import Protocol
from uuid import UUID

from sqlalchemy.orm import InstrumentedAttribute

from app.exceptions import NoEntityFoundError
from app.io.entity import EntityCreate, EntityOrderBy, EntityUpdate, OrderDirection
from app.model.entity import Entity
from app.repository.base import Ordering

_ORDER_COLUMNS: Mapping[EntityOrderBy, InstrumentedAttribute[object]] = {
    EntityOrderBy.NAME: Entity.name,
    EntityOrderBy.DESCRIPTION: Entity.description,
    EntityOrderBy.CREATED_AT: Entity.created_at,
    EntityOrderBy.UPDATED_AT: Entity.updated_at,
}


class EntityStore(Protocol):
    async def save(self, entity: Entity) -> Entity: ...

    async def find_by_id(self, entity_id: UUID) -> Entity | None: ...

    async def find_all_paginated(
        self,
        offset: int = 0,
        limit: int = 25,
        ordering: Ordering | None = None,
    ) -> Sequence[Entity]: ...

    async def update(self, entity: Entity) -> Entity: ...

    async def delete_by_id(self, entity_id: UUID) -> bool: ...


class EntityService:
    def __init__(self, repo: EntityStore) -> None:
        self.repo = repo

    async def create(self, data: EntityCreate) -> Entity:
        entity = Entity(name=data.name, description=data.description)
        return await self.repo.save(entity)

    async def get_by_id(self, entity_id: UUID) -> Entity:
        entity = await self.repo.find_by_id(entity_id)
        if entity is None:
            raise NoEntityFoundError(entity_id)
        return entity

    async def get_all(
        self,
        offset: int = 0,
        limit: int = 25,
        order_by: EntityOrderBy = EntityOrderBy.CREATED_AT,
        order_direction: OrderDirection = OrderDirection.ASC,
    ) -> Sequence[Entity]:
        ordering = Ordering(
            column=_ORDER_COLUMNS[order_by],
            descending=order_direction is OrderDirection.DESC,
        )
        return await self.repo.find_all_paginated(
            offset=offset,
            limit=limit,
            ordering=ordering,
        )

    async def update(self, entity_id: UUID, data: EntityUpdate) -> Entity:
        entity = await self.repo.find_by_id(entity_id)
        if entity is None:
            raise NoEntityFoundError(entity_id)

        entity.name = data.name
        entity.description = data.description
        return await self.repo.update(entity)

    async def delete(self, entity_id: UUID) -> None:
        deleted = await self.repo.delete_by_id(entity_id)
        if not deleted:
            raise NoEntityFoundError(entity_id)
