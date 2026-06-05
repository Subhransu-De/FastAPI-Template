from abc import ABC, abstractmethod
from collections.abc import Sequence
from typing import Any
from uuid import UUID

from sqlalchemy import ColumnElement

from app.model.base import Base


class PrimaryRepository[ModelType: Base](ABC):
    @abstractmethod
    async def find_by_id(self, entity_id: UUID) -> ModelType | None:
        pass

    @abstractmethod
    async def find_all(self) -> Sequence[ModelType]:
        pass

    @abstractmethod
    async def find_all_by_id(self, ids: list[UUID]) -> Sequence[ModelType]:
        pass

    @abstractmethod
    async def find_all_paginated(
        self, offset: int = 0, limit: int = 25, order_by: ColumnElement | None = None
    ) -> Sequence[ModelType]:
        pass

    @abstractmethod
    async def find_by(self, **kwargs: Any) -> Sequence[ModelType]:
        pass

    @abstractmethod
    async def save(self, entity: ModelType) -> ModelType:
        pass

    @abstractmethod
    async def save_all(self, entities: list[ModelType]) -> list[ModelType]:
        pass

    @abstractmethod
    async def update(self, entity: ModelType) -> ModelType:
        pass

    @abstractmethod
    async def exists_by_id(self, entity_id: UUID) -> bool:
        pass

    @abstractmethod
    async def delete_by_id(self, entity_id: UUID) -> bool:
        pass

    @abstractmethod
    async def delete_all_by_id(self, ids: list[UUID]) -> int:
        pass
