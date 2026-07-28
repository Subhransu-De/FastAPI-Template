from collections.abc import Callable
from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session
from app.repository.entity import EntityRepository
from app.repository.petclinic import PetClinicRepository
from app.service.entity import EntityService
from app.service.petclinic import PetClinicService


def service_dependency[RepoT, ServiceT](
    service_type: Callable[[RepoT], ServiceT],
    repository_type: Callable[[AsyncSession], RepoT],
) -> Callable[[AsyncSession], ServiceT]:
    def dependency(
        # FastAPI 0.139 supports scope; Sonar's dependency model is outdated.
        session: Annotated[
            AsyncSession,
            Depends(get_session, scope="function"),  # NOSONAR
        ],
    ) -> ServiceT:
        return service_type(repository_type(session))

    return dependency


get_entity_service = service_dependency(EntityService, EntityRepository)
get_petclinic_service = service_dependency(PetClinicService, PetClinicRepository)

__all__ = [
    "EntityService",
    "PetClinicService",
    "get_entity_service",
    "get_petclinic_service",
]
