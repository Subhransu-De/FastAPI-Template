import pytest


pytestmark = pytest.mark.integration


async def test_health_db(client):
    response = await client.get("/health/db")

    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}
