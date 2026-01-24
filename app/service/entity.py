from functools import lru_cache
from sys import maxsize
from uuid import UUID

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session
from app.io.entity import EntityCreate, EntityUpdate
from app.model.entity import Entity
from app.repository.entity import EntityRepository


class EntityService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.repo = EntityRepository(session)

    async def create(self, data: EntityCreate) -> Entity:
        entity = Entity(name=data.name, description=data.description)
        entity = await self.repo.save(entity)
        await self.session.commit()
        return entity

    async def get_by_id(self, id: UUID) -> Entity | None:
        return await self.repo.find_by_id(id)

    async def get_all(self, offset: int = 0, limit: int = 25) -> list[Entity]:
        entities = await self.repo.find_all_paginated(offset=offset, limit=limit)
        return list(entities)

    async def update(self, id: UUID, data: EntityUpdate) -> Entity | None:
        entity = await self.repo.find_by_id(id)
        if entity is None:
            return None

        if data.name is not None:
            entity.name = data.name
        if data.description is not None:
            entity.description = data.description

        entity = await self.repo.update(entity)
        await self.session.commit()
        return entity

    async def delete(self, id: UUID) -> bool:
        exists = await self.repo.exists_by_id(id)
        if not exists:
            return False
        await self.repo.delete_by_id(id)
        await self.session.commit()
        return True


async def get_entity_service(
    session: AsyncSession = Depends(get_session),
) -> EntityService:
    return EntityService(session)
