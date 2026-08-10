import re
from typing import Any
from weakref import WeakSet

import logfire
from fastapi import FastAPI, Request, WebSocket
from sqlalchemy.engine import Engine
from sqlalchemy.ext.asyncio import AsyncEngine

from app.observability.configuration import configure_observability

_instrumented_fastapi_apps: WeakSet[FastAPI] = WeakSet()
_instrumented_sqlalchemy_engines: WeakSet[Engine] = WeakSet()
EXCLUDED_FASTAPI_PATHS = [
    "/health",
]


def _excluded_url_patterns() -> list[str]:
    return [rf".*{re.escape(path)}(?:\?.*)?$" for path in EXCLUDED_FASTAPI_PATHS]


def _extract_client_ip(request: Request | WebSocket) -> str | None:
    forwarded_for = request.headers.get("x-forwarded-for")
    if forwarded_for:
        return forwarded_for.split(",", maxsplit=1)[0].strip()

    if request.client is None:
        return None

    return request.client.host


def _add_auth_attributes(
    request: Request | WebSocket,
    attributes: dict[str, Any],
) -> None:
    claims = getattr(request.state, "auth_claims", None)
    if not isinstance(claims, dict):
        return

    client_id = claims.get("azp") or claims.get("client_id")
    audience = claims.get("aud")
    issuer = claims.get("iss")

    if client_id:
        attributes["oidc.client_id"] = client_id
    if audience:
        attributes["oidc.audience"] = audience
    if issuer:
        attributes["oidc.issuer"] = issuer


def _request_attributes_mapper(
    request: Request | WebSocket,
    attributes: dict[str, Any],
) -> dict[str, Any]:
    mapped_attributes: dict[str, Any] = {}
    if errors := attributes.get("errors"):
        mapped_attributes["errors"] = errors

    client_ip = _extract_client_ip(request)
    if client_ip:
        mapped_attributes["client.ip"] = client_ip

    _add_auth_attributes(request, mapped_attributes)
    return mapped_attributes


def instrument_fastapi(app: FastAPI) -> None:
    configure_observability()
    if app in _instrumented_fastapi_apps:
        return

    logfire.instrument_fastapi(
        app,
        request_attributes_mapper=_request_attributes_mapper,
        excluded_urls=_excluded_url_patterns(),
    )
    _instrumented_fastapi_apps.add(app)


def instrument_sqlalchemy(engine: AsyncEngine | Engine) -> None:
    configure_observability()
    instrumented_engine = (
        engine.sync_engine if isinstance(engine, AsyncEngine) else engine
    )
    if instrumented_engine in _instrumented_sqlalchemy_engines:
        return

    logfire.instrument_sqlalchemy(engine=instrumented_engine)
    _instrumented_sqlalchemy_engines.add(instrumented_engine)
