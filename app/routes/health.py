from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session

route = APIRouter()


@route.get("/health/db")
async def health_db(session: AsyncSession = Depends(get_session)):
    try:
        await session.execute(select(1))
        return {"status": "healthy"}
    except Exception:
        raise HTTPException(status_code=503, detail="Database unhealthy")
