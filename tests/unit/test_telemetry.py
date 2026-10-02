import re

import logfire
import pytest
from fastapi import Request
from logfire.testing import CaptureLogfire

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


def test_request_attributes_mapper_keeps_errors_and_client_ip_only() -> None:
    attributes: dict[str, object] = {
        "values": {"payload": {"description": "private"}},
        "errors": [{"loc": ["body", "name"], "msg": "missing"}],
    }

    mapped = telemetry._request_attributes_mapper(_request(), attributes)

    assert mapped == {
        "errors": [{"loc": ["body", "name"], "msg": "missing"}],
        "client.ip": "203.0.113.42",
    }


def test_request_attributes_mapper_ignores_values_left_on_request_state() -> None:
    mapped = telemetry._request_attributes_mapper(
        _request(auth_attributes={"client_id": "spoofed"}),
        {},
    )

    assert mapped == {"client.ip": "203.0.113.42"}


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
