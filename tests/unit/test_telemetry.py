import httpx
import logfire
import pytest
from fastapi import Depends, FastAPI
from logfire.testing import CaptureLogfire

from app import telemetry

pytestmark = pytest.mark.unit


def test_configure_otel_configures_logfire_once_per_service(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[dict[str, object]] = []

    def configure(**kwargs: object) -> None:
        calls.append(kwargs)

    monkeypatch.setattr(telemetry.logfire, "configure", configure)

    telemetry.configure_otel("service-under-test")
    telemetry.configure_otel("service-under-test")

    assert len(calls) == 1
    assert calls[0]["service_name"] == "service-under-test"
    assert calls[0]["send_to_logfire"] == "if-token-present"


def test_record_auth_attributes_tags_the_active_span(capfire: CaptureLogfire) -> None:
    with logfire.span("request"):
        telemetry.record_auth_attributes(
            telemetry.AuthAttributes(
                client_id="api-client",
                audience=("api", "docs"),
                issuer="https://idp.example",
            )
        )

    (span,) = capfire.exporter.exported_spans_as_dict()
    assert span["attributes"]["oidc.client_id"] == "api-client"
    assert span["attributes"]["oidc.audience"] == ("api", "docs")
    assert span["attributes"]["oidc.issuer"] == "https://idp.example"


def test_record_auth_attributes_is_a_no_op_without_an_active_span(
    capfire: CaptureLogfire,
) -> None:
    telemetry.record_auth_attributes(
        telemetry.AuthAttributes(
            client_id=None, audience="api", issuer="https://idp.example"
        )
    )

    assert capfire.exporter.exported_spans_as_dict() == []


def _authenticated() -> None:
    telemetry.record_auth_attributes(
        telemetry.AuthAttributes(
            client_id="api-client", audience="api", issuer="https://idp.example"
        )
    )


def _instrumented_app() -> FastAPI:
    app = FastAPI(telemetry=telemetry.native_telemetry_config())
    app.add_middleware(telemetry.ServerSpanMiddleware)

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "up"}

    @app.get("/items/{item_id}", dependencies=[Depends(_authenticated)])
    def item(item_id: int) -> dict[str, int]:
        return {"id": item_id}

    return app


async def _get(app: FastAPI, path: str) -> httpx.Response:
    transport = httpx.ASGITransport(app=app, client=("203.0.113.42", 4242))
    async with httpx.AsyncClient(transport=transport, base_url="http://api") as client:
        return await client.get(path)


async def test_native_request_span_carries_client_and_auth_attributes(
    capfire: CaptureLogfire,
) -> None:
    response = await _get(_instrumented_app(), "/items/7")

    assert response.status_code == 200
    spans = capfire.exporter.exported_spans_as_dict()
    (server,) = [span for span in spans if span["name"] == "GET /items/{item_id}"]
    assert server["attributes"]["http.route"] == "/items/{item_id}"
    assert server["attributes"]["http.response.status_code"] == 200
    assert server["attributes"]["client.address"] == "203.0.113.42"
    assert server["attributes"]["oidc.client_id"] == "api-client"
    assert server["attributes"]["oidc.audience"] == "api"
    assert server["attributes"]["oidc.issuer"] == "https://idp.example"
    (dependencies,) = [s for s in spans if s["name"] == "fastapi.dependencies"]
    assert "oidc.client_id" not in dependencies["attributes"]


async def test_native_telemetry_skips_health_probes(capfire: CaptureLogfire) -> None:
    response = await _get(_instrumented_app(), "/health")

    assert response.status_code == 200
    assert not [
        span
        for span in capfire.exporter.exported_spans_as_dict()
        if span["attributes"].get("logfire.span_type") == "span"
    ]
