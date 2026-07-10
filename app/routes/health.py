from fastapi import APIRouter

route = APIRouter()


@route.get("/health")
async def health() -> dict[str, str]:
    return {"status": "up"}
