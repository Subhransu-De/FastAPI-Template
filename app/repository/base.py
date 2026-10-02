from collections.abc import Sequence
from dataclasses import dataclass
from uuid import UUID

from sqlalchemy import ColumnElement, delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import InstrumentedAttribute

from app.model.base import Base


@dataclass(frozen=True, slots=True)
class Ordering:
    column: InstrumentedAttribute[object]
    descending: bool = False


class Repository[ModelType: Base]:
    def __init__(self, model: type[ModelType], session: AsyncSession) -> None:
        self.model = model
        self.session = session

    async def find_by_id(self, entity_id: UUID) -> ModelType | None:
        return await self.session.get(self.model, entity_id)

    async def find_all(self) -> Sequence[ModelType]:
        result = await self.session.execute(select(self.model))
        return result.scalars().all()

    async def find_all_by_id(self, ids: Sequence[UUID]) -> Sequence[ModelType]:
        if not ids:
            return []
        result = await self.session.execute(
            select(self.model).where(self.model.id.in_(ids))
        )
        return result.scalars().all()

    async def find_all_paginated(
        self,
        offset: int = 0,
        limit: int = 25,
        ordering: Ordering | None = None,
    ) -> Sequence[ModelType]:
        query = select(self.model)

        if ordering is not None:
            clause = (
                ordering.column.desc() if ordering.descending else ordering.column.asc()
            )
            query = query.order_by(clause)

        result = await self.session.execute(query.offset(offset).limit(limit))
        return result.scalars().all()

    async def find_by(self, *criteria: ColumnElement[bool]) -> Sequence[ModelType]:
        result = await self.session.execute(select(self.model).where(*criteria))
        return result.scalars().all()

    async def save(self, entity: ModelType) -> ModelType:
        self.session.add(entity)
        await self.session.flush()
        await self.session.refresh(entity)
        return entity

    async def save_all(self, entities: Sequence[ModelType]) -> Sequence[ModelType]:
        self.session.add_all(entities)
        await self.session.flush()
        for entity in entities:
            await self.session.refresh(entity)
        return entities

    async def update(self, entity: ModelType) -> ModelType:
        updated = await self.session.merge(entity)
        await self.session.flush()
        await self.session.refresh(updated)
        return updated

    async def exists_by_id(self, entity_id: UUID) -> bool:
        result = await self.session.execute(
            select(func.count())
            .select_from(self.model)
            .where(self.model.id == entity_id)
        )
        return result.scalar_one() > 0

    async def delete_by_id(self, entity_id: UUID) -> bool:
        return await self.delete_all_by_id([entity_id]) > 0

    async def delete_all_by_id(self, ids: Sequence[UUID]) -> int:
        if not ids:
            return 0
        result = await self.session.execute(
            delete(self.model).where(self.model.id.in_(ids)).returning(self.model.id)
        )
        await self.session.flush()
        return len(result.scalars().all())
