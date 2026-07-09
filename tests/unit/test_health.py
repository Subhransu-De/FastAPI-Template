from unittest.mock import AsyncMock

import pytest
from sqlalchemy.exc import OperationalError

from app.exceptions import DatabaseUnavailableError
from app.routes.health import health

pytestmark = pytest.mark.unit


async def test_health_executes_database_probe() -> None:
    session = AsyncMock()

    result = await health(session)

    statement = session.execute.await_args.args[0]
    assert str(statement) == "SELECT 1"
    assert result == {"status": "up"}


async def test_health_reports_database_unavailable() -> None:
    session = AsyncMock()
    session.execute.side_effect = OperationalError(
        "SELECT 1",
        {},
        RuntimeError("database unavailable"),
    )

    with pytest.raises(DatabaseUnavailableError):
        await health(session)
