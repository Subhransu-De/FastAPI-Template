from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI

from app import logger
from app.routes import health_route
from app.settings import settings

logger.setup_logging()


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info(f"Starting up {settings.app_name} on port {settings.port}")
    app.include_router(health_route)
    yield
    logger.info("Application shutdown")


app = FastAPI(title=settings.app_name, lifespan=lifespan)


def main():
    uvicorn.run("app.main:app", host="0.0.0.0", port=settings.port, reload=True)


if __name__ == "__main__":
    main()
