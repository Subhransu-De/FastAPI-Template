import httpx
import pytest

pytestmark = pytest.mark.integration


async def test_health_db_returns_healthy(app_client: httpx.AsyncClient) -> None:
    response = await app_client.get("/health/db")

    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}
