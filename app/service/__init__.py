from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session
from app.repository.entity import EntityRepository
from app.service.entity import EntityService, EntityStore


def get_entity_service(
    session: Annotated[AsyncSession, Depends(get_session, scope="function")],  # NOSONAR
) -> EntityService:
    return EntityService(EntityRepository(session))


__all__ = ["EntityService", "EntityStore", "get_entity_service"]
