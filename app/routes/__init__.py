from fastapi import APIRouter, Depends

from app.auth import authenticate_request
from app.routes.entity import route as entity_route
from app.routes.health import route as health_route
from app.routes.petclinic import route as petclinic_route

public_route = APIRouter()
public_route.include_router(health_route)

protected_route = APIRouter(dependencies=[Depends(authenticate_request)])
protected_route.include_router(entity_route)
protected_route.include_router(petclinic_route)

__all__ = ["protected_route", "public_route"]
