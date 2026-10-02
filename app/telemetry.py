import re
from dataclasses import dataclass
from functools import cache

import logfire
from fastapi import FastAPI, Request, WebSocket
from fastapi.telemetry import TelemetryConfig
from starlette.types import Scope

HEALTH_ENDPOINT_PATHS: tuple[str, ...] = ("/health", "/health/ready")

_FASTAPI_EXCLUDED_URLS = (
    ".*(?:"
    + "|".join(re.escape(path) for path in HEALTH_ENDPOINT_PATHS)
    + r")(?:\?.*)?$"
)


@dataclass(frozen=True, slots=True)
class AuthAttributes:
    client_id: str | None
    audience: str | tuple[str, ...]
    issuer: str


@cache
def configure_otel(service_name: str) -> None:
    logfire.configure(
        service_name=service_name,
        send_to_logfire="if-token-present",
        console=logfire.ConsoleOptions(colors="never", show_project_link=False),
    )


def record_auth_attributes(request: Request, attributes: AuthAttributes) -> None:
    request.state.auth_attributes = attributes


def _auth_attributes(request: Request | WebSocket) -> AuthAttributes | None:
    try:
        attributes = request.state.auth_attributes
    except AttributeError:
        return None
    return attributes if isinstance(attributes, AuthAttributes) else None


def _request_attributes_mapper(
    request: Request | WebSocket,
    attributes: dict[str, object],
) -> dict[str, object]:
    mapped_attributes: dict[str, object] = {}
    if errors := attributes.get("errors"):
        mapped_attributes["errors"] = errors

    if request.client is not None:
        mapped_attributes["client.ip"] = request.client.host

    auth = _auth_attributes(request)
    if auth is not None:
        if auth.client_id:
            mapped_attributes["oidc.client_id"] = auth.client_id
        mapped_attributes["oidc.audience"] = (
            list(auth.audience) if isinstance(auth.audience, tuple) else auth.audience
        )
        mapped_attributes["oidc.issuer"] = auth.issuer
    return mapped_attributes


def instrument_fastapi(app: FastAPI) -> None:
    logfire.instrument_fastapi(
        app,
        request_attributes_mapper=_request_attributes_mapper,
        excluded_urls=_FASTAPI_EXCLUDED_URLS,
    )


@cache
def instrument_sqlalchemy() -> None:
    logfire.instrument_sqlalchemy(skip_dep_check=True)


def _is_health_probe(scope: Scope) -> bool:
    return scope.get("path") in HEALTH_ENDPOINT_PATHS


def native_telemetry_config() -> TelemetryConfig:
    return {"auto_configure": False, "exclude": _is_health_probe}
