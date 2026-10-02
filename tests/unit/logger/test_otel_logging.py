import logging

import logfire
import pytest
from logfire.testing import CaptureLogfire
from opentelemetry import trace

from app.logger import configuration

pytestmark = pytest.mark.unit


def test_setup_logging_exports_stdlib_logs_to_otel(capfire: CaptureLogfire) -> None:
    configuration.setup_logging(
        otel_handler_factory=lambda: logfire.LogfireLoggingHandler(
            fallback=logging.NullHandler()
        )
    )

    with trace.get_tracer(__name__).start_as_current_span("correlated request") as span:
        span_context = span.get_span_context()
        logging.getLogger("third.party").info(
            "third-party log captured",
            extra={"component": "unit-test"},
        )
    logging.getLogger("uvicorn.access").warning("uvicorn access captured")

    exported = capfire.exporter.exported_spans_as_dict(parse_json_attributes=True)
    logs = [
        record
        for record in exported
        if record["attributes"].get("logfire.span_type") == "log"
    ]
    messages = [record["attributes"].get("logfire.msg") for record in logs]
    third_party_log = next(
        record
        for record in logs
        if record["attributes"].get("logfire.msg") == "third-party log captured"
    )

    assert "third-party log captured" in messages
    assert "uvicorn access captured" in messages
    assert third_party_log["attributes"].get("component") == "unit-test"
    assert third_party_log["context"]["trace_id"] == span_context.trace_id
    assert third_party_log["context"]["span_id"] != span_context.span_id
    assert third_party_log["parent"]["span_id"] == span_context.span_id
