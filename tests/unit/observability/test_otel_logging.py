import logging

import logfire
import pytest
from logfire.testing import TestExporter
from opentelemetry import trace
from opentelemetry.sdk.trace.export import SimpleSpanProcessor

from app.observability import logging as observability_logging

pytestmark = pytest.mark.unit


def test_setup_logging_exports_stdlib_logs_to_otel() -> None:
    exporter = TestExporter()
    logfire.configure(
        send_to_logfire=False,
        console=False,
        service_name="fastapi-template-test",
        additional_span_processors=[SimpleSpanProcessor(exporter)],
    )

    observability_logging.setup_logging(
        handler_factory=lambda: logfire.LogfireLoggingHandler(
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

    exported = exporter.exported_spans_as_dict(parse_json_attributes=True)
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
