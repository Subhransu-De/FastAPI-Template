from fastapi import APIRouter

route = APIRouter()


@route.get("/health", tags=["health"])
async def health_check():
    return {"status": "ok"}