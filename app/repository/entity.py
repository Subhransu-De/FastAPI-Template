from sqlalchemy.ext.asyncio import AsyncSession

from app.model.entity import Entity
from app.repository.base import BaseRepository


class EntityRepository(BaseRepository[Entity]):
    def __init__(self, session: AsyncSession):
        super().__init__(Entity, session)
