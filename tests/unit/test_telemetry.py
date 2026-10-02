import re

import pytest
from fastapi import Request

from app import telemetry

pytestmark = pytest.mark.unit


def _request(**state: object) -> Request:
    return Request(
        {
            "type": "http",
            "client": ("203.0.113.42", 4242),
            "headers": [],
            "state": state,
        }
    )


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


def test_request_attributes_mapper_keeps_errors_client_ip_and_auth() -> None:
    request = _request()
    telemetry.record_auth_attributes(
        request,
        telemetry.AuthAttributes(
            client_id="api-client",
            audience=("api", "docs"),
            issuer="https://idp.example",
        ),
    )
    attributes: dict[str, object] = {
        "values": {"payload": {"description": "private"}},
        "errors": [{"loc": ["body", "name"], "msg": "missing"}],
    }

    mapped = telemetry._request_attributes_mapper(request, attributes)

    assert mapped == {
        "errors": [{"loc": ["body", "name"], "msg": "missing"}],
        "client.ip": "203.0.113.42",
        "oidc.client_id": "api-client",
        "oidc.audience": ["api", "docs"],
        "oidc.issuer": "https://idp.example",
    }
    assert "values" not in mapped


def test_request_attributes_mapper_ignores_requests_without_auth() -> None:
    mapped = telemetry._request_attributes_mapper(_request(), {})

    assert mapped == {"client.ip": "203.0.113.42"}


def test_request_attributes_mapper_ignores_foreign_state_values() -> None:
    mapped = telemetry._request_attributes_mapper(
        _request(auth_attributes={"client_id": "spoofed"}),
        {},
    )

    assert "oidc.client_id" not in mapped


@pytest.mark.parametrize(
    ("url", "excluded"),
    [
        ("http://api/health", True),
        ("http://api/health?probe=1", True),
        ("http://api/health/ready", True),
        ("http://api/healthz", False),
        ("http://api/entities/", False),
    ],
)
def test_excluded_urls_pattern_matches_only_health_endpoints(
    url: str,
    *,
    excluded: bool,
) -> None:
    assert bool(re.match(telemetry._FASTAPI_EXCLUDED_URLS, url)) is excluded
