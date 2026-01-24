from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query

from app.io.entity import EntityCreate, EntityResponse, EntityUpdate
from app.service import EntityService, get_entity_service

route = APIRouter(prefix="/entities", tags=["entities"])


@route.post("/", response_model=EntityResponse, status_code=201)
async def create_entity(
    data: EntityCreate, service: EntityService = Depends(get_entity_service)
) -> EntityResponse:
    entity = await service.create(data)
    return EntityResponse.model_validate(entity)


@route.get("/{id}", response_model=EntityResponse)
async def get_entity(
    id: UUID, service: EntityService = Depends(get_entity_service)
) -> EntityResponse:
    entity = await service.get_by_id(id)
    if entity is None:
        raise HTTPException(status_code=404, detail="Entity not found")
    return EntityResponse.model_validate(entity)


@route.get("/", response_model=list[EntityResponse])
async def list_entities(
    offset: int = Query(0, ge=0),
    limit: int = Query(25, ge=1, le=100),
    service: EntityService = Depends(get_entity_service),
) -> list[EntityResponse]:
    entities = await service.get_all(offset=offset, limit=limit)
    return [EntityResponse.model_validate(e) for e in entities]


@route.put("/{id}", response_model=EntityResponse)
async def update_entity(
    id: UUID, data: EntityUpdate, service: EntityService = Depends(get_entity_service)
) -> EntityResponse:
    entity = await service.update(id, data)
    if entity is None:
        raise HTTPException(status_code=404, detail="Entity not found")
    return EntityResponse.model_validate(entity)


@route.delete("/{id}", status_code=204)
async def delete_entity(
    id: UUID, service: EntityService = Depends(get_entity_service)
) -> None:
    deleted = await service.delete(id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Entity not found")
