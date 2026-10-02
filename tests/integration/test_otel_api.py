import json
from uuid import uuid4

import httpx
import pytest
from logfire.testing import CaptureLogfire

from tests.integration.conftest import WithAuth
from tests.support import TEST_CLIENT_ID, TEST_ISSUER

pytestmark = pytest.mark.integration


@WithAuth
async def test_entity_api_requests_emit_otel_records(
    capfire: CaptureLogfire,
    app_client: httpx.AsyncClient,
) -> None:
    create_response = await app_client.post(
        "/entities/",
        json={"name": "OTEL entity", "description": "private description"},
    )
    assert create_response.status_code == 201
    missing_entity_id = uuid4()

    missing_response = await app_client.get(f"/entities/{missing_entity_id}")
    assert missing_response.status_code == 404
    assert (await app_client.get("/health")).status_code == 200
    assert (await app_client.get("/health/ready")).status_code == 200

    exported = capfire.exporter.exported_spans_as_dict(parse_json_attributes=True)
    request_records = [
        span
        for span in exported
        if span["attributes"].get("logfire.span_type") == "span"
        and span["attributes"].get("http.route")
    ]
    actual_requests = [
        (
            span["attributes"].get("http.method"),
            span["attributes"].get("http.route"),
            span["attributes"].get("http.status_code"),
        )
        for span in request_records
    ]

    assert ("POST", "/entities/", 201) in actual_requests
    assert ("GET", "/entities/{entity_id}", 404) in actual_requests
    assert not [route for _, route, _ in actual_requests if route.startswith("/health")]

    post_record = next(
        span
        for span in request_records
        if span["attributes"].get("http.method") == "POST"
        and span["attributes"].get("http.route") == "/entities/"
    )
    assert post_record["attributes"].get("client.ip") == "127.0.0.1"
    assert post_record["attributes"].get("oidc.client_id") == TEST_CLIENT_ID
    assert post_record["attributes"].get("oidc.audience") == TEST_CLIENT_ID
    assert post_record["attributes"].get("oidc.issuer") == TEST_ISSUER

    statements = [
        span["attributes"]["db.statement"]
        for span in exported
        if "db.statement" in span["attributes"]
    ]
    assert any(statement.startswith("INSERT INTO entities") for statement in statements)

    serialized_attributes = json.dumps(
        [span["attributes"] for span in exported],
        default=str,
    )
    assert "private description" not in serialized_attributes
    assert "Bearer " not in serialized_attributes
    assert "authorization" not in serialized_attributes.lower()
