from collections.abc import AsyncGenerator
from unittest.mock import AsyncMock

import httpx
import pytest
from sqlalchemy.exc import OperationalError
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session
from app.main import app

pytestmark = pytest.mark.integration


async def test_health_returns_up_after_database_probe(
    app_client: httpx.AsyncClient,
) -> None:
    response = await app_client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "up"}


async def test_unknown_route_returns_problem_details(
    app_client: httpx.AsyncClient,
) -> None:
    response = await app_client.get("/not-a-route")

    assert response.status_code == 404
    assert response.headers["content-type"] == "application/problem+json"
    assert response.json() == {
        "type": "about:blank",
        "title": "Not Found",
        "status": 404,
        "detail": "Not Found",
        "instance": "https://testserver/not-a-route",
    }


async def test_health_returns_service_unavailable_problem_when_database_fails(
    app_client: httpx.AsyncClient,
) -> None:
    session = AsyncMock(spec=AsyncSession)
    session.execute.side_effect = OperationalError(
        "SELECT 1",
        {},
        RuntimeError("database unavailable"),
    )

    async def unavailable_session() -> AsyncGenerator[AsyncSession]:
        yield session

    app.dependency_overrides[get_session] = unavailable_session

    response = await app_client.get("/health")

    assert response.status_code == 503
    assert response.headers["content-type"] == "application/problem+json"
    assert response.json() == {
        "type": "https://testserver/openapi.json",
        "title": "Service Unavailable",
        "status": 503,
        "detail": "The database is unavailable.",
        "instance": "https://testserver/health",
    }
