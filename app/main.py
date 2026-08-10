import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException

from app import observability
from app.auth import AccessTokenValidator, OIDCOpenAPIFastAPI
from app.database.engine import get_engine
from app.exceptions import AuthenticationError, BaseError, base_exception_handler
from app.routes import protected_route, public_route
from app.settings import app_settings, authn_settings, resolve_oidc_metadata

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncGenerator[None]:
    observability.setup_logging()
    oidc_metadata = await resolve_oidc_metadata(authn_settings)
    _app.state.oidc_metadata = oidc_metadata
    _app.state.access_token_validator = AccessTokenValidator(
        oidc_metadata,
        audience=authn_settings.client_id,
        jwks_cache_ttl_seconds=authn_settings.jwks_cache_ttl_seconds,
    )
    _app.openapi_schema = None
    observability.instrument_sqlalchemy(get_engine())
    logger.info(
        "Starting up %s on port %s",
        app_settings.app_name,
        app_settings.port,
    )
    try:
        yield
    finally:
        await get_engine().dispose()
        logger.info("Application shutdown")


app = OIDCOpenAPIFastAPI(
    title=app_settings.app_name,
    lifespan=lifespan,
    swagger_ui_init_oauth={
        "clientId": authn_settings.docs_client_id,
        "scopes": "openid",
        "usePkceWithAuthorizationCodeGrant": True,
    },
)
observability.instrument_fastapi(app)

app.add_exception_handler(AuthenticationError, base_exception_handler)
app.add_exception_handler(BaseError, base_exception_handler)
app.add_exception_handler(RequestValidationError, base_exception_handler)
app.add_exception_handler(HTTPException, base_exception_handler)
app.add_exception_handler(Exception, base_exception_handler)

app.include_router(public_route)
app.include_router(protected_route)


def main() -> None:
    observability.setup_logging()
    uvicorn.run(
        "app.main:app",
        host=app_settings.host,
        port=app_settings.port,
        reload=app_settings.reload,
        log_config=None,
    )


if __name__ == "__main__":
    main()
