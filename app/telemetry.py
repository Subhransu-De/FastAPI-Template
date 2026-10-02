import re
from dataclasses import dataclass
from functools import cache

import logfire
from fastapi import FastAPI, Request, WebSocket
from fastapi.telemetry import TelemetryConfig
from opentelemetry import trace
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


def record_auth_attributes(attributes: AuthAttributes) -> None:
    span = trace.get_current_span()
    if not span.is_recording():
        return
    if attributes.client_id:
        span.set_attribute("oidc.client_id", attributes.client_id)
    span.set_attribute(
        "oidc.audience",
        list(attributes.audience)
        if isinstance(attributes.audience, tuple)
        else attributes.audience,
    )
    span.set_attribute("oidc.issuer", attributes.issuer)


def _request_attributes_mapper(
    request: Request | WebSocket,
    attributes: dict[str, object],
) -> dict[str, object]:
    mapped_attributes: dict[str, object] = {}
    if errors := attributes.get("errors"):
        mapped_attributes["errors"] = errors

    if request.client is not None:
        mapped_attributes["client.ip"] = request.client.host
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
