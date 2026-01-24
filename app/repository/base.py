from typing import Any, Generic, Optional, Sequence, Type, TypeVar
from uuid import UUID

from sqlalchemy import ColumnElement, Result, delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.model.base import Base

ModelType = TypeVar("ModelType", bound=Base)


class BaseRepository(Generic[ModelType]):
    def __init__(self, model: Type[ModelType], session: AsyncSession):
        self.model = model
        self.session = session

    async def find_by_id(self, id: UUID) -> Optional[ModelType]:
        return await self.session.get(self.model, id)

    async def find_all(self) -> Sequence[ModelType]:
        result: Result[Any] = await self.session.execute(select(self.model))
        return result.scalars().all()

    async def find_all_by_id(self, ids: list[UUID]) -> Sequence[ModelType]:
        if not ids:
            return []
        result: Result[Any] = await self.session.execute(
            select(self.model).where(self.model.id.in_(ids))
        )
        return result.scalars().all()

    async def find_all_paginated(
        self, offset: int = 0, limit: int = 25, order_by: ColumnElement | None = None
    ) -> Sequence[ModelType]:
        query = select(self.model)

        if order_by is not None:
            query = query.order_by(order_by)

        query = query.offset(offset).limit(limit)
        result: Result[Any] = await self.session.execute(query)
        return result.scalars().all()

    async def find_by(self, **kwargs: Any) -> Sequence[ModelType]:
        query = select(self.model)
        for key, value in kwargs.items():
            query = query.where(getattr(self.model, key) == value)
        result: Result[Any] = await self.session.execute(query)
        return result.scalars().all()

    async def save(self, entity: ModelType) -> ModelType:
        self.session.add(entity)
        await self.session.flush()
        await self.session.refresh(entity)
        return entity

    async def save_all(self, entities: list[ModelType]) -> list[ModelType]:
        self.session.add_all(entities)
        await self.session.flush()
        for entity in entities:
            await self.session.refresh(entity)
        return entities

    async def update(self, entity: ModelType) -> ModelType:
        updated: ModelType = await self.session.merge(entity)
        await self.session.flush()
        return updated

    async def exists_by_id(self, id: UUID) -> bool:
        result: Result[Any] = await self.session.execute(
            select(func.count()).select_from(self.model).where(self.model.id == id)
        )
        return result.scalar_one() > 0

    async def delete_by_id(self, id: UUID) -> bool:
        result: Result[Any] = await self.session.execute(
            delete(self.model).where(self.model.id == id)
        )
        await self.session.flush()
        return len(result.scalars().all()) > 0

    async def delete_all_by_id(self, ids: list[UUID]) -> int:
        if not ids:
            return 0
        result: Result[Any] = await self.session.execute(
            delete(self.model).where(self.model.id.in_(ids))
        )
        await self.session.flush()
        return len(result.scalars().all())
