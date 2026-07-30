import importlib
import runpy
import sys
from unittest.mock import AsyncMock, Mock

import httpx
import pytest
from fastapi import FastAPI
from starlette.exceptions import HTTPException

from app.exceptions import base_exception_handler
from app.settings import OIDCMetadata

pytestmark = pytest.mark.unit


def test_swagger_uses_public_pkce_client_without_a_secret() -> None:
    module = importlib.import_module("app.main")

    assert module.app.swagger_ui_init_oauth == {
        "clientId": "fastapi-docs",
        "scopes": "openid",
        "usePkceWithAuthorizationCodeGrant": True,
    }


def test_main_registers_problem_details_handlers() -> None:
    module = importlib.import_module("app.main")

    assert module.app.exception_handlers[HTTPException] is base_exception_handler
    assert module.app.exception_handlers[Exception] is base_exception_handler


async def test_catch_all_returns_problem_details_for_unknown_error() -> None:
    test_app = FastAPI()
    test_app.add_exception_handler(Exception, base_exception_handler)

    @test_app.get("/failure")
    async def failure() -> None:
        message = "sensitive diagnostic"
        raise RuntimeError(message)

    transport = httpx.ASGITransport(
        app=test_app,
        raise_app_exceptions=False,
    )
    async with httpx.AsyncClient(
        transport=transport,
        base_url="https://testserver",
    ) as client:
        response = await client.get("/failure")

    assert response.status_code == 500
    assert response.headers["content-type"] == "application/problem+json"
    assert response.json() == {
        "type": "about:blank",
        "title": "Internal Server Error",
        "status": 500,
        "detail": "An unexpected error occurred.",
        "instance": "https://testserver/failure",
    }


async def test_lifespan_runs_startup_and_shutdown(monkeypatch):
    module = importlib.import_module("app.main")

    setup_logging = Mock()
    info = Mock()
    metadata = OIDCMetadata(
        jwks_uri="https://idp.example/jwks",
        issuer="https://idp.example",
        authorization_endpoint="https://idp.example/authorize",
        token_endpoint="https://idp.example/token",  # noqa: S106
    )
    resolve_oidc_metadata = AsyncMock(return_value=metadata)
    access_token_validator = Mock()
    access_token_validator_class = Mock(return_value=access_token_validator)
    permission_authorizer = AsyncMock()
    role_manager = Mock()
    create_keycloak_clients = Mock(
        return_value=(permission_authorizer, role_manager)
    )

    monkeypatch.setattr(module.logger, "setup_logging", setup_logging)
    monkeypatch.setattr(module.logfire, "info", info)
    monkeypatch.setattr(module, "resolve_oidc_metadata", resolve_oidc_metadata)
    monkeypatch.setattr(
        module,
        "AccessTokenValidator",
        access_token_validator_class,
    )
    monkeypatch.setattr(
        module,
        "create_keycloak_clients",
        create_keycloak_clients,
    )

    async with module.lifespan(module.app):
        setup_logging.assert_called_once_with()
        info.assert_called_once_with(
            "Starting up {service_name} on port {port}",
            service_name=module.app_settings.app_name,
            port=module.app_settings.port,
        )
        assert module.app.state.oidc_metadata is metadata
        assert module.app.state.access_token_validator is access_token_validator
        assert module.app.state.permission_authorizer is permission_authorizer
        assert module.app.state.role_manager is role_manager

    resolve_oidc_metadata.assert_awaited_once_with(module.authn_settings)
    access_token_validator_class.assert_called_once_with(
        metadata,
        audience=module.authn_settings.client_id,
        jwks_cache_ttl_seconds=module.authn_settings.jwks_cache_ttl_seconds,
    )
    create_keycloak_clients.assert_called_once_with(
        realm_url=module.authn_settings.internal_url
        or module.authn_settings.issuer_url,
        client_id=module.authn_settings.client_id,
        client_secret=module.authn_settings.client_secret.get_secret_value(),
        resource_name=module.authn_settings.authorization_resource,
        timeout_seconds=module.authn_settings.authorization_timeout_seconds,
    )
    info.assert_any_call("Application shutdown")
    permission_authorizer.close.assert_awaited_once_with()


def test_main_runs_uvicorn(monkeypatch):
    module = importlib.import_module("app.main")
    run = Mock()
    setup_logging = Mock()

    monkeypatch.setattr(module.uvicorn, "run", run)
    monkeypatch.setattr(module.logger, "setup_logging", setup_logging)

    module.main()

    setup_logging.assert_called_once_with()
    run.assert_called_once_with(
        "app.main:app",
        host=module.app_settings.host,
        port=module.app_settings.port,
        reload=module.app_settings.reload,
        log_config=None,
    )


def test_running_module_as_script_calls_main(monkeypatch):
    run = Mock()
    existing_module = sys.modules.pop("app.main", None)

    monkeypatch.setattr("uvicorn.run", run)

    try:
        runpy.run_module("app.main", run_name="__main__")
    finally:
        if existing_module is not None:
            sys.modules["app.main"] = existing_module

    run.assert_called_once()
