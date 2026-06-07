from fastapi import APIRouter, Depends

from app.auth import authentication_filter
from app.routes.entity import route as entity_route
from app.routes.health import route as health_route

public_route = APIRouter()
public_route.include_router(health_route)

protected_route = APIRouter(dependencies=[Depends(authentication_filter)])
protected_route.include_router(entity_route)

__all__ = ["protected_route", "public_route"]
