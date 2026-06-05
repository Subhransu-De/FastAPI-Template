from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query

from app.auth import authentication_filter
from app.exceptions import NoEntityFoundError
from app.io.entity import EntityCreate, EntityResponse, EntityUpdate
from app.service import EntityService, get_entity_service

route = APIRouter(prefix="/entities", tags=["entities"])


@route.post("/", status_code=201)
async def create_entity(
    data: EntityCreate,
    service: Annotated[EntityService, Depends(get_entity_service)],
    _: Annotated[None, Depends(authentication_filter)],
) -> EntityResponse:
    entity = await service.create(data)
    return EntityResponse.model_validate(entity)


@route.get("/{entity_id}")
async def get_entity(
    entity_id: UUID,
    service: Annotated[EntityService, Depends(get_entity_service)],
    _: Annotated[None, Depends(authentication_filter)],
) -> EntityResponse:
    entity = await service.get_by_id(entity_id)
    if entity is None:
        raise NoEntityFoundError(entity_id)
    return EntityResponse.model_validate(entity)


@route.get("/")
async def list_entities(
    service: Annotated[EntityService, Depends(get_entity_service)],
    _: Annotated[None, Depends(authentication_filter)],
    offset: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = 25,
) -> list[EntityResponse]:
    entities = await service.get_all(offset=offset, limit=limit)
    return [EntityResponse.model_validate(e) for e in entities]


@route.put("/{entity_id}")
async def update_entity(
    entity_id: UUID,
    data: EntityUpdate,
    service: Annotated[EntityService, Depends(get_entity_service)],
    _: Annotated[None, Depends(authentication_filter)],
) -> EntityResponse:
    entity = await service.update(entity_id, data)
    if entity is None:
        raise NoEntityFoundError(entity_id)
    return EntityResponse.model_validate(entity)


@route.delete("/{entity_id}", status_code=204)
async def delete_entity(
    entity_id: UUID,
    service: Annotated[EntityService, Depends(get_entity_service)],
    _: Annotated[None, Depends(authentication_filter)],
) -> None:
    await service.delete(entity_id)
