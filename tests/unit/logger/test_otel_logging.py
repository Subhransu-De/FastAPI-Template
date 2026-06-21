import json
import logging

import logfire
import pytest
from logfire.testing import TestExporter
from opentelemetry.sdk.trace.export import SimpleSpanProcessor

import app.logger.logger as logger_module
from app.logger.handlers import JSON_LOG_ATTRIBUTE, JsonPayloadLogfireLoggingHandler

pytestmark = pytest.mark.unit


def test_setup_logging_exports_app_and_uvicorn_logs_to_otel(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    exporter = TestExporter()
    logfire.configure(
        send_to_logfire=False,
        console=False,
        service_name="fastapi-template-test",
        additional_span_processors=[SimpleSpanProcessor(exporter)],
    )
    def get_test_otel_log_handler() -> logging.Handler:
        return JsonPayloadLogfireLoggingHandler()

    monkeypatch.setattr(
        logger_module,
        "get_otel_log_handler",
        get_test_otel_log_handler,
    )

    logger_module.setup_logging()

    logging.getLogger(logger_module.app_settings.app_name).info(
        "app log %s",
        "captured",
        extra={"component": "unit-test"},
    )
    logging.getLogger("uvicorn.access").warning("uvicorn access captured")
    logging.getLogger("third.party").error("third-party propagated captured")

    exported = exporter.exported_spans_as_dict(parse_json_attributes=True)
    messages = [span["attributes"].get("logfire.msg") for span in exported]
    app_log = next(
        span
        for span in exported
        if span["attributes"].get("logfire.msg") == "app log captured"
    )
    json_payload = app_log["attributes"][JSON_LOG_ATTRIBUTE]
    if isinstance(json_payload, str):
        json_payload = json.loads(json_payload)

    assert "app log captured" in messages
    assert "uvicorn access captured" in messages
    assert "third-party propagated captured" in messages
    assert all(
        span["attributes"].get("logfire.span_type") == "log" for span in exported
    )
    assert any(
        span["attributes"].get("component") == "unit-test" for span in exported
    )
    assert json_payload["message"] == "app log captured"
    assert json_payload["severity_text"] == "INFO"
    assert json_payload["severity_number"] == 9
    assert json_payload["attributes"]["component"] == "unit-test"
