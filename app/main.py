from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

import uvicorn
from alembic.config import Config
from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError

from alembic import command
from app import logger, telemetry
from app.database.engine import get_engine
from app.exceptions import AuthenticationError, BaseError, base_exception_handler
from app.routes import protected_route, public_route
from app.settings import app_settings, authn_settings


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncGenerator[None]:
    logger.setup_logging()
    telemetry.instrument_sqlalchemy(get_engine())
    alembic_cfg = Config("alembic.ini")
    alembic_cfg.set_main_option("script_location", "alembic")
    command.upgrade(alembic_cfg, "head")
    logger.info(f"Starting up {app_settings.app_name} on port {app_settings.port}")
    yield
    await get_engine().dispose()
    logger.info("Application shutdown")


app = FastAPI(
    title=app_settings.app_name,
    lifespan=lifespan,
    swagger_ui_init_oauth={
        "clientId": authn_settings.client_id,
        "clientSecret": authn_settings.client_secret,
        "scopes": "openid",
        "usePkceWithAuthorizationCodeGrant": True,
    },
)
telemetry.instrument_fastapi(app)

app.add_exception_handler(AuthenticationError, base_exception_handler)
app.add_exception_handler(BaseError, base_exception_handler)
app.add_exception_handler(RequestValidationError, base_exception_handler)

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
