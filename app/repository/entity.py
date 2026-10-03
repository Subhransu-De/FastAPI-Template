from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.model.entity import Entity
from app.repository.base import Repository


class EntityRepository(Repository[Entity, UUID]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(Entity, session)
