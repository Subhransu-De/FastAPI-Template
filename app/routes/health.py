from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session

route = APIRouter()


@route.get("/health/db")
async def health_db(session: AsyncSession = Depends(get_session)):
    return {"status": "healthy"}
