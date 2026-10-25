from dataclasses import dataclass
from functools import cache

import logfire
from fastapi.telemetry import TelemetryConfig
from opentelemetry import context, trace
from starlette.types import ASGIApp, Receive, Scope, Send

HEALTH_ENDPOINT_PATHS: tuple[str, ...] = ("/health", "/health/ready")

_SERVER_SPAN_KEY = "app.telemetry.server_span"


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


def _server_span() -> trace.Span:
    span = context.get_value(_SERVER_SPAN_KEY)
    return span if isinstance(span, trace.Span) else trace.get_current_span()


def record_auth_attributes(attributes: AuthAttributes) -> None:
    span = _server_span()
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


class ServerSpanMiddleware:
    """Tag FastAPI's request span and keep it reachable from dependencies.

    FastAPI starts the server span outside the middleware stack and runs
    dependencies inside a `fastapi.dependencies` child span, so request-level
    attributes must be set on the span that is current here.
    """

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        span = trace.get_current_span()
        if (
            scope["type"] not in ("http", "websocket")
            or _is_health_probe(scope)
            or not span.is_recording()
        ):
            await self.app(scope, receive, send)
            return
        client = scope.get("client")
        if client:
            span.set_attribute("client.address", client[0])
        token = context.attach(context.set_value(_SERVER_SPAN_KEY, span))
        try:
            await self.app(scope, receive, send)
        finally:
            context.detach(token)


@cache
def instrument_sqlalchemy() -> None:
    logfire.instrument_sqlalchemy(skip_dep_check=True)


def _is_health_probe(scope: Scope) -> bool:
    return scope.get("path") in HEALTH_ENDPOINT_PATHS


def native_telemetry_config() -> TelemetryConfig:
    return {"auto_configure": False, "exclude": _is_health_probe}
