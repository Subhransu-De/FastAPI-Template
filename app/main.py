from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import TypedDict

import logfire
import uvicorn
from fastapi.exceptions import RequestValidationError
from sqlalchemy.exc import OperationalError
from starlette.exceptions import HTTPException

from app import logger, telemetry
from app.auth import AccessTokenValidator, OIDCOpenAPIFastAPI
from app.database import SessionMaker, create_engine, create_sessionmaker
from app.exceptions import BaseError, base_exception_handler
from app.routes import protected_route, public_route
from app.settings import Settings, resolve_oidc_metadata


class LifespanState(TypedDict):
    sessionmaker: SessionMaker
    access_validator: AccessTokenValidator


@asynccontextmanager
async def lifespan(app: OIDCOpenAPIFastAPI) -> AsyncIterator[LifespanState]:
    settings = app.settings
    logger.setup_logging()
    oidc_metadata = await resolve_oidc_metadata(settings.oidc)
    app.oidc_metadata = oidc_metadata
    app.openapi_schema = None
    engine = create_engine(settings.database)
    logfire.info(
        "Starting up {service_name} on port {port}",
        service_name=settings.app.app_name,
        port=settings.app.port,
    )
    try:
        yield {
            "sessionmaker": create_sessionmaker(engine),
            "access_validator": AccessTokenValidator(
                oidc_metadata,
                audience=settings.oidc.client_id,
                jwks_cache_ttl_seconds=settings.oidc.jwks_cache_ttl_seconds,
                jwks_refresh_cooldown_seconds=(
                    settings.oidc.jwks_refresh_cooldown_seconds
                ),
            ),
        }
    finally:
        await engine.dispose()
        logfire.info("Application shutdown")


def create_app(settings: Settings) -> OIDCOpenAPIFastAPI:
    telemetry.configure_otel(settings.app.app_name)
    app = OIDCOpenAPIFastAPI(settings=settings, lifespan=lifespan)
    telemetry.instrument_fastapi(app)
    telemetry.instrument_sqlalchemy()

    for exception_type in (
        BaseError,
        RequestValidationError,
        OperationalError,
        HTTPException,
        Exception,
    ):
        app.add_exception_handler(exception_type, base_exception_handler)

    app.include_router(public_route)
    app.include_router(protected_route)
    return app


def app_from_env() -> OIDCOpenAPIFastAPI:
    return create_app(Settings.from_env())


def main() -> None:
    settings = Settings.from_env()
    telemetry.configure_otel(settings.app.app_name)
    logger.setup_logging()
    uvicorn.run(
        "app.main:app_from_env",
        factory=True,
        host=settings.app.host,
        port=settings.app.port,
        reload=settings.app.reload,
        log_config=None,
        proxy_headers=settings.app.proxy_headers,
        forwarded_allow_ips=settings.app.forwarded_allow_ips,
    )


if __name__ == "__main__":
    main()
