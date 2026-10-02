import asyncio
from http import HTTPStatus
from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from app.database import SessionMaker, get_sessionmaker
from app.exceptions import DatabaseUnavailableError, problem_responses
from app.io.health import HealthResponse

READINESS_TIMEOUT_SECONDS = 1.0

route = APIRouter(tags=["health"])


@route.get("/health")
async def health() -> HealthResponse:
    return HealthResponse()


@route.get(
    "/health/ready",
    responses=problem_responses(HTTPStatus.SERVICE_UNAVAILABLE),
)
async def readiness(
    sessionmaker: Annotated[SessionMaker, Depends(get_sessionmaker)],
) -> HealthResponse:
    try:
        async with (
            asyncio.timeout(READINESS_TIMEOUT_SECONDS),
            sessionmaker() as session,
        ):
            await session.execute(text("SELECT 1"))
    except (OSError, SQLAlchemyError) as error:
        raise DatabaseUnavailableError from error
    return HealthResponse()
