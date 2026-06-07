from collections.abc import Callable
from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session
from app.repository.entity import EntityRepository
from app.service.entity import EntityService


def service_dependency[RepoT, ServiceT](
    service_type: Callable[[RepoT], ServiceT],
    repository_type: Callable[[AsyncSession], RepoT],
) -> Callable[[AsyncSession], ServiceT]:
    def dependency(
        session: Annotated[AsyncSession, Depends(get_session)],
    ) -> ServiceT:
        return service_type(repository_type(session))

    return dependency


get_entity_service = service_dependency(EntityService, EntityRepository)

__all__ = ["EntityService", "get_entity_service"]
