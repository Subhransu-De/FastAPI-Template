import logging
from typing import Any

import logfire
from fastapi import FastAPI, Request, WebSocket
from sqlalchemy.ext.asyncio import AsyncEngine

from app.settings import app_settings

_configured = False
_instrumented_fastapi_apps: set[int] = set()
_instrumented_sqlalchemy_engines: set[int] = set()


def configure_otel() -> None:
    global _configured
    if _configured:
        return

    logfire.configure(
        service_name=app_settings.app_name,
        send_to_logfire=False,
        console=False,
    )
    _configured = True


def get_otel_log_handler() -> logging.Handler:
    configure_otel()
    handler = logfire.LogfireLoggingHandler()
    handler.setLevel(logging.INFO)
    return handler


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
    client_ip = _extract_client_ip(request)
    if client_ip:
        attributes["client.ip"] = client_ip

    _add_auth_attributes(request, attributes)
    return attributes


def instrument_fastapi(app: FastAPI) -> None:
    configure_otel()
    app_id = id(app)
    if app_id in _instrumented_fastapi_apps:
        return

    logfire.instrument_fastapi(app, request_attributes_mapper=_request_attributes_mapper)
    _instrumented_fastapi_apps.add(app_id)


def instrument_sqlalchemy(engine: AsyncEngine) -> None:
    configure_otel()
    engine_id = id(engine)
    if engine_id in _instrumented_sqlalchemy_engines:
        return

    logfire.instrument_sqlalchemy(engine=engine)
    _instrumented_sqlalchemy_engines.add(engine_id)
