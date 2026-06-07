from unittest.mock import AsyncMock

import pytest

from app.routes.health import health_db

pytestmark = pytest.mark.unit


async def test_health_db_returns_up():
    session = AsyncMock()
    result = await health_db(session)
    assert result == {"status": "up"}
