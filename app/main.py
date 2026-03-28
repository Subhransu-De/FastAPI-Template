from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

import uvicorn
from alembic.config import Config
from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError

from alembic import command
from app import logger
from app.exceptions import BaseError, base_exception_handler
from app.routes import entity_route, health_route
from app.settings import settings


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncGenerator[None]:
    logger.setup_logging()
    alembic_cfg = Config("alembic.ini")
    alembic_cfg.set_main_option("script_location", "alembic")
    command.upgrade(alembic_cfg, "head")
    logger.info(f"Starting up {settings.app_name} on port {settings.port}")
    yield
    logger.info("Application shutdown")


app = FastAPI(title=settings.app_name, lifespan=lifespan)

app.add_exception_handler(BaseError, base_exception_handler)
app.add_exception_handler(RequestValidationError, base_exception_handler)

app.include_router(health_route)
app.include_router(entity_route)


def main() -> None:
    uvicorn.run("app.main:app", host="0.0.0.0", port=settings.port, reload=True)  # noqa: S104


if __name__ == "__main__":
    main()
