from http import HTTPStatus

from fastapi import APIRouter, Depends

from app.auth import authenticate_request
from app.exceptions import problem_responses
from app.routes.entity import route as entity_route
from app.routes.health import route as health_route

public_route = APIRouter()
public_route.include_router(health_route)

protected_route = APIRouter(
    dependencies=[Depends(authenticate_request)],
    responses=problem_responses(
        HTTPStatus.UNAUTHORIZED,
        HTTPStatus.UNPROCESSABLE_CONTENT,
    ),
)
protected_route.include_router(entity_route)

__all__ = ["protected_route", "public_route"]
