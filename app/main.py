from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError

from app import logger
from app.exceptions import BaseException, base_exception_handler
from app.routes import entity_route, health_route
from app.settings import settings

logger.setup_logging()


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info(f"Starting up {settings.app_name} on port {settings.port}")
    yield
    logger.info("Application shutdown")


app = FastAPI(title=settings.app_name, lifespan=lifespan)

app.add_exception_handler(BaseException, base_exception_handler)
app.add_exception_handler(RequestValidationError, base_exception_handler)

app.include_router(health_route)
app.include_router(entity_route)


def main():
    uvicorn.run("app.main:app", host="0.0.0.0", port=settings.port, reload=True)


if __name__ == "__main__":
    main()
