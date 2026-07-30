from collections.abc import Sequence
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query

from app.auth import Permission, require_permissions
from app.io.entity import (
    EntityCreate,
    EntityOrderBy,
    EntityResponse,
    EntityUpdate,
    OrderDirection,
)
from app.model.entity import Entity
from app.service import EntityService, get_entity_service

route = APIRouter(prefix="/entities", tags=["entities"])


@route.post(
    "/",
    status_code=201,
    response_model=EntityResponse,
    dependencies=[Depends(require_permissions(Permission.ENTITY_CREATE))],
)
async def create_entity(
    data: EntityCreate,
    service: Annotated[EntityService, Depends(get_entity_service)],
) -> Entity:
    return await service.create(data)


@route.get(
    "/{entity_id}",
    response_model=EntityResponse,
    dependencies=[Depends(require_permissions(Permission.ENTITY_READ))],
)
async def get_entity(
    entity_id: UUID,
    service: Annotated[EntityService, Depends(get_entity_service)],
) -> Entity:
    return await service.get_by_id(entity_id)


@route.get(
    "/",
    response_model=list[EntityResponse],
    dependencies=[Depends(require_permissions(Permission.ENTITY_LIST))],
)
async def list_entities(
    service: Annotated[EntityService, Depends(get_entity_service)],
    offset: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = 25,
    order_by: EntityOrderBy = EntityOrderBy.CREATED_AT,
    order_direction: OrderDirection = OrderDirection.ASC,
) -> Sequence[Entity]:
    return await service.get_all(
        offset=offset,
        limit=limit,
        order_by=order_by,
        order_direction=order_direction,
    )


@route.put(
    "/{entity_id}",
    response_model=EntityResponse,
    dependencies=[Depends(require_permissions(Permission.ENTITY_UPDATE))],
)
async def update_entity(
    entity_id: UUID,
    data: EntityUpdate,
    service: Annotated[EntityService, Depends(get_entity_service)],
) -> Entity:
    return await service.update(entity_id, data)


@route.delete(
    "/{entity_id}",
    status_code=204,
    dependencies=[Depends(require_permissions(Permission.ENTITY_DELETE))],
)
async def delete_entity(
    entity_id: UUID,
    service: Annotated[EntityService, Depends(get_entity_service)],
) -> None:
    await service.delete(entity_id)
