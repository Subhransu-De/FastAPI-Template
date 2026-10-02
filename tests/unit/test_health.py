import httpx
import pytest
from asgi_lifespan import LifespanManager

from app.database import SessionMaker, create_engine, create_sessionmaker
from app.exceptions import DatabaseUnavailableError
from app.io.health import HealthResponse
from app.main import create_app
from app.routes.health import health, readiness
from app.settings import Settings
from tests.support import UNREACHABLE_DATABASE_URL, build_settings

pytestmark = pytest.mark.unit


@pytest.fixture
def unreachable_settings() -> Settings:
    return build_settings(database_url=UNREACHABLE_DATABASE_URL)


async def test_health_reports_the_application_is_up() -> None:
    assert await health() == HealthResponse(status="up")


async def test_readiness_succeeds_when_the_database_answers(
    sqlite_sessionmaker: SessionMaker,
) -> None:
    assert await readiness(sqlite_sessionmaker) == HealthResponse(status="up")


async def test_readiness_fails_when_the_database_is_unreachable(
    unreachable_settings: Settings,
) -> None:
    engine = create_engine(unreachable_settings.database)
    sessionmaker = create_sessionmaker(engine)
    try:
        with pytest.raises(DatabaseUnavailableError):
            await readiness(sessionmaker)
    finally:
        await engine.dispose()


async def test_probes_over_http_when_the_database_is_down(
    unreachable_settings: Settings,
) -> None:
    app = create_app(unreachable_settings)

    async with LifespanManager(app) as manager:
        transport = httpx.ASGITransport(app=manager.app)
        async with httpx.AsyncClient(
            transport=transport, base_url="https://testserver"
        ) as client:
            live = await client.get("/health")
            ready = await client.get("/health/ready")

    assert live.status_code == 200
    assert live.json() == {"status": "up"}
    assert ready.status_code == 503
    assert ready.headers["content-type"] == "application/problem+json"
    assert ready.json() == {
        "type": "https://testserver/openapi.json",
        "title": "Service Unavailable",
        "status": 503,
        "detail": "The database is unavailable.",
        "instance": "https://testserver/health/ready",
    }
