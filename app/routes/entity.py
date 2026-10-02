from collections.abc import Sequence
from http import HTTPStatus
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query

from app.auth import ENTITY_WRITE_ROLE, require_role
from app.exceptions import problem_responses
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

_writer = Depends(require_role(ENTITY_WRITE_ROLE))


@route.post(
    "/",
    status_code=HTTPStatus.CREATED,
    response_model=EntityResponse,
    dependencies=[_writer],
    responses=problem_responses(HTTPStatus.FORBIDDEN),
)
async def create_entity(
    data: EntityCreate,
    service: Annotated[EntityService, Depends(get_entity_service)],
) -> Entity:
    return await service.create(data)


@route.get(
    "/{entity_id}",
    response_model=EntityResponse,
    responses=problem_responses(HTTPStatus.NOT_FOUND),
)
async def get_entity(
    entity_id: UUID,
    service: Annotated[EntityService, Depends(get_entity_service)],
) -> Entity:
    return await service.get_by_id(entity_id)


@route.get("/", response_model=list[EntityResponse])
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
    dependencies=[_writer],
    responses=problem_responses(HTTPStatus.FORBIDDEN, HTTPStatus.NOT_FOUND),
)
async def update_entity(
    entity_id: UUID,
    data: EntityUpdate,
    service: Annotated[EntityService, Depends(get_entity_service)],
) -> Entity:
    return await service.update(entity_id, data)


@route.delete(
    "/{entity_id}",
    status_code=HTTPStatus.NO_CONTENT,
    dependencies=[_writer],
    responses=problem_responses(HTTPStatus.FORBIDDEN, HTTPStatus.NOT_FOUND),
)
async def delete_entity(
    entity_id: UUID,
    service: Annotated[EntityService, Depends(get_entity_service)],
) -> None:
    await service.delete(entity_id)
