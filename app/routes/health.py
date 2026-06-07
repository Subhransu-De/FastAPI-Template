from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session

route = APIRouter()


@route.get("/health/db")
async def health_db(
    _session: Annotated[AsyncSession, Depends(get_session)],
) -> dict[str, str]:
    return {"status": "up"}
