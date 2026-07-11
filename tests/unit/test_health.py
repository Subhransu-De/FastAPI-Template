import pytest

from app.routes.health import health

pytestmark = pytest.mark.unit


async def test_health_reports_the_application_is_up() -> None:
    assert await health() == {"status": "up"}
