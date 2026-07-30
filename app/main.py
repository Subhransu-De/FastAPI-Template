from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

import logfire
import uvicorn
from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException

from app import logger, telemetry
from app.auth import (
    AccessTokenValidator,
    OIDCOpenAPIFastAPI,
    create_keycloak_clients,
)
from app.database.engine import get_engine
from app.exceptions import AuthenticationError, BaseError, base_exception_handler
from app.routes import protected_route, public_route
from app.settings import app_settings, authn_settings, resolve_oidc_metadata


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncGenerator[None]:
    logger.setup_logging()
    oidc_metadata = await resolve_oidc_metadata(authn_settings)
    _app.state.oidc_metadata = oidc_metadata
    _app.state.access_token_validator = AccessTokenValidator(
        oidc_metadata,
        audience=authn_settings.client_id,
        jwks_cache_ttl_seconds=authn_settings.jwks_cache_ttl_seconds,
    )
    permission_authorizer, role_manager = create_keycloak_clients(
        realm_url=authn_settings.internal_url or authn_settings.issuer_url,
        client_id=authn_settings.client_id,
        client_secret=authn_settings.client_secret.get_secret_value(),
        resource_name=authn_settings.authorization_resource,
        timeout_seconds=authn_settings.authorization_timeout_seconds,
    )
    _app.state.permission_authorizer = permission_authorizer
    _app.state.role_manager = role_manager
    _app.openapi_schema = None
    telemetry.instrument_sqlalchemy(get_engine())
    logfire.info(
        "Starting up {service_name} on port {port}",
        service_name=app_settings.app_name,
        port=app_settings.port,
    )
    try:
        yield
    finally:
        await permission_authorizer.close()
        await get_engine().dispose()
        logfire.info("Application shutdown")


app = OIDCOpenAPIFastAPI(
    title=app_settings.app_name,
    lifespan=lifespan,
    swagger_ui_init_oauth={
        "clientId": authn_settings.docs_client_id,
        "scopes": "openid",
        "usePkceWithAuthorizationCodeGrant": True,
    },
)
telemetry.instrument_fastapi(app)

app.add_exception_handler(AuthenticationError, base_exception_handler)
app.add_exception_handler(BaseError, base_exception_handler)
app.add_exception_handler(RequestValidationError, base_exception_handler)
app.add_exception_handler(HTTPException, base_exception_handler)
app.add_exception_handler(Exception, base_exception_handler)

app.include_router(public_route)
app.include_router(protected_route)


def main() -> None:
    logger.setup_logging()
    uvicorn.run(
        "app.main:app",
        host=app_settings.host,
        port=app_settings.port,
        reload=app_settings.reload,
        log_config=None,
    )


if __name__ == "__main__":
    main()
