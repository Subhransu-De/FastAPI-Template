from collections.abc import Sequence
from uuid import UUID

from app.exceptions import NoEntityFoundError
from app.io.entity import EntityCreate, EntityUpdate
from app.model.entity import Entity
from app.repository.entity import EntityRepository


class EntityService:
    def __init__(self, repo: EntityRepository) -> None:
        self.repo = repo

    async def create(self, data: EntityCreate) -> Entity:
        entity = Entity(name=data.name, description=data.description)
        return await self.repo.save(entity)

    async def get_by_id(self, entity_id: UUID) -> Entity:
        entity = await self.repo.find_by_id(entity_id)
        if entity is None:
            raise NoEntityFoundError(entity_id)
        return entity

    async def get_all(self, offset: int = 0, limit: int = 25) -> Sequence[Entity]:
        return await self.repo.find_all_paginated(offset=offset, limit=limit)

    async def update(self, entity_id: UUID, data: EntityUpdate) -> Entity:
        entity = await self.repo.find_by_id(entity_id)
        if entity is None:
            raise NoEntityFoundError(entity_id)

        entity.apply_changes(data)

        return await self.repo.update(entity)

    async def delete(self, entity_id: UUID) -> None:
        deleted = await self.repo.delete_by_id(entity_id)
        if not deleted:
            raise NoEntityFoundError(entity_id)

