from unittest.mock import Mock

import httpx
import pytest
from asgi_lifespan import LifespanManager
from sqlalchemy.exc import OperationalError
from sqlalchemy.ext.asyncio import async_sessionmaker

from app import main as main_module
from app.auth import AccessTokenValidator, OIDCOpenAPIFastAPI
from app.main import app_from_env, create_app, lifespan
from app.settings import Settings
from tests.support import TEST_DOCS_CLIENT_ID

pytestmark = pytest.mark.unit


def test_create_app_configures_a_public_pkce_docs_client(settings: Settings) -> None:
    app = create_app(settings)

    assert app.title == settings.app.app_name
    assert app.swagger_ui_init_oauth == {
        "clientId": TEST_DOCS_CLIENT_ID,
        "scopes": "openid",
        "usePkceWithAuthorizationCodeGrant": True,
    }


async def test_lifespan_yields_typed_state_and_publishes_oidc_metadata(
    settings: Settings,
) -> None:
    app = create_app(settings)

    async with lifespan(app) as state:
        assert isinstance(state["sessionmaker"], async_sessionmaker)
        assert isinstance(state["access_validator"], AccessTokenValidator)
        assert app.oidc_metadata == settings.oidc.metadata_override()


async def test_requests_reach_the_lifespan_owned_validator(
    settings: Settings,
) -> None:
    app = create_app(settings)

    async with LifespanManager(app) as manager:
        transport = httpx.ASGITransport(app=manager.app)
        async with httpx.AsyncClient(
            transport=transport, base_url="https://testserver"
        ) as client:
            response = await client.get(
                "/entities/", headers={"Authorization": "Bearer not-a-jwt"}
            )

    assert response.status_code == 401
    assert response.headers["WWW-Authenticate"] == "Bearer"
    assert response.json()["title"] == "Unauthorized"


async def _probe(
    settings: Settings,
    error: Exception,
) -> httpx.Response:
    app = create_app(settings)

    @app.get("/probe")
    async def probe() -> None:
        raise error

    async with LifespanManager(app) as manager:
        transport = httpx.ASGITransport(app=manager.app, raise_app_exceptions=False)
        async with httpx.AsyncClient(
            transport=transport, base_url="https://testserver"
        ) as client:
            return await client.get("/probe")


async def test_unexpected_errors_become_problem_details_without_leaking(
    settings: Settings,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    logged: list[tuple[object, ...]] = []
    monkeypatch.setattr(
        "app.exceptions.handlers.logfire.exception",
        lambda *args, **_kwargs: logged.append(args),
    )

    response = await _probe(settings, RuntimeError("sensitive diagnostic"))

    assert response.status_code == 500
    assert response.headers["content-type"] == "application/problem+json"
    assert response.json() == {
        "type": "about:blank",
        "title": "Internal Server Error",
        "status": 500,
        "detail": "An unexpected error occurred.",
        "instance": "https://testserver/probe",
    }
    assert "sensitive diagnostic" not in response.text
    assert len(logged) == 1


async def test_database_connection_failures_become_service_unavailable(
    settings: Settings,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "app.exceptions.handlers.logfire.exception",
        lambda *_args, **_kwargs: None,
    )
    error = OperationalError("SELECT 1", {}, ConnectionRefusedError())

    response = await _probe(settings, error)

    assert response.status_code == 503
    assert response.headers["content-type"] == "application/problem+json"
    assert response.json() == {
        "type": "https://testserver/openapi.json",
        "title": "Service Unavailable",
        "status": 503,
        "detail": "The database is unavailable.",
        "instance": "https://testserver/probe",
    }


def test_app_from_env_builds_the_application_from_settings(
    monkeypatch: pytest.MonkeyPatch,
    settings: Settings,
) -> None:
    monkeypatch.setattr(main_module.Settings, "from_env", lambda: settings)

    app = app_from_env()

    assert isinstance(app, OIDCOpenAPIFastAPI)
    assert app.settings is settings


def test_main_runs_uvicorn_with_the_application_factory(
    monkeypatch: pytest.MonkeyPatch,
    settings: Settings,
) -> None:
    run = Mock()
    monkeypatch.setattr(main_module.Settings, "from_env", lambda: settings)
    monkeypatch.setattr(main_module.uvicorn, "run", run)

    main_module.main()

    run.assert_called_once_with(
        "app.main:app_from_env",
        factory=True,
        host=settings.app.host,
        port=settings.app.port,
        reload=settings.app.reload,
        log_config=None,
        proxy_headers=settings.app.proxy_headers,
        forwarded_allow_ips=settings.app.forwarded_allow_ips,
    )
