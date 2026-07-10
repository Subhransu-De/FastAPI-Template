import httpx
import pytest

pytestmark = pytest.mark.integration


async def test_health_returns_application_status(
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
