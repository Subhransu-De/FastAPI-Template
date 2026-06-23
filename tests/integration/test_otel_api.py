import httpx
import logfire
import pytest
from logfire.testing import TestExporter
from opentelemetry.sdk.trace.export import SimpleSpanProcessor

from tests.integration.conftest import WithAuth

pytestmark = pytest.mark.integration


@pytest.fixture
def otel_exporter() -> TestExporter:
    return TestExporter()


@WithAuth
async def test_entity_api_requests_emit_otel_records(
    otel_exporter: TestExporter,
    app_client: httpx.AsyncClient,
) -> None:
    logfire.configure(
        send_to_logfire=False,
        console=False,
        service_name="fastapi-template-test",
        additional_span_processors=[SimpleSpanProcessor(otel_exporter)],
    )
    otel_exporter.clear()

    create_response = await app_client.post(
        "/entities/",
        headers={"X-Forwarded-For": "203.0.113.42"},
        json={"name": "OTEL entity", "description": "Created through OTEL test"},
    )
    assert create_response.status_code == 201
    entity_id = create_response.json()["id"]

    get_response = await app_client.get(f"/entities/{entity_id}")
    list_response = await app_client.get("/entities/")
    update_response = await app_client.put(
        f"/entities/{entity_id}",
        json={"name": "OTEL entity updated"},
    )
    delete_response = await app_client.delete(f"/entities/{entity_id}")
    missing_response = await app_client.get(f"/entities/{entity_id}")

    assert get_response.status_code == 200
    assert list_response.status_code == 200
    assert update_response.status_code == 200
    assert delete_response.status_code == 204
    assert missing_response.status_code == 404

    exported = otel_exporter.exported_spans_as_dict(parse_json_attributes=True)
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
    post_record = next(
        span
        for span in request_records
        if span["attributes"].get("http.method") == "POST"
        and span["attributes"].get("http.route") == "/entities/"
    )
    assert post_record["attributes"].get("client.ip") == "203.0.113.42"
    assert post_record["attributes"].get("oidc.client_id") == "test-client"
    assert post_record["attributes"].get("oidc.audience") == "test-client"
    assert post_record["attributes"].get("oidc.issuer") == "https://test-idp/realm"
    assert ("GET", f"/entities/{entity_id}", 200) in actual_requests
    assert ("GET", "/entities/", 200) in actual_requests
    assert ("PUT", f"/entities/{entity_id}", 200) in actual_requests
    assert ("DELETE", f"/entities/{entity_id}", 204) in actual_requests
    assert ("GET", f"/entities/{entity_id}", 404) in actual_requests
