import time

import httpx

from app.settings import settings

_keys: dict[str, dict] = {}
_fetched_at: float = 0.0


def _jwks_url() -> str:
    return (
        f"{settings.keycloak_url}/realms/{settings.keycloak_realm}"
        "/protocol/openid-connect/certs"
    )


async def fetch_jwks() -> None:
    global _keys, _fetched_at
    async with httpx.AsyncClient() as client:
        resp = await client.get(_jwks_url())
        resp.raise_for_status()
    data = resp.json()
    _keys = {k["kid"]: k for k in data["keys"]}
    _fetched_at = time.monotonic()


async def get_public_key(kid: str) -> dict | None:
    ttl = settings.keycloak_jwks_cache_ttl_minutes * 60
    if time.monotonic() - _fetched_at >= ttl:
        await fetch_jwks()
    return _keys.get(kid)
