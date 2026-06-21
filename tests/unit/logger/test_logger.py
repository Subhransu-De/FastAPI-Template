import json
import logging
import sys
from datetime import UTC, datetime
from io import StringIO
from unittest.mock import Mock
from uuid import UUID

import pytest

import app.logger.formatters as formatter_module
import app.logger.logger as logger_module
from app.logger.handlers import (
    JSON_LOG_ATTRIBUTE,
    JsonPayloadLogfireLoggingHandler,
)

pytestmark = pytest.mark.unit


def _raise_value_error() -> None:
    message = "boom"
    raise ValueError(message)


def test_json_formatter_formats_record_without_exception():
    formatter = logger_module.JsonFormatter()
    record = logging.LogRecord(
        name="test.logger",
        level=logging.INFO,
        pathname=__file__,
        lineno=10,
        msg="hello world",
        args=(),
        exc_info=None,
    )

    payload = json.loads(formatter.format(record))

    assert payload["name"] == "test.logger"
    assert payload["level"] == "INFO"
    assert payload["message"] == "hello world"
    assert payload["severity_text"] == "INFO"
    assert payload["severity_number"] == 9
    assert payload["body"] == "hello world"
    assert payload["resource"]["service.name"] == logger_module.app_settings.app_name
    assert payload["scope"]["name"] == "test.logger"
    assert payload["attributes"]["logger.name"] == "test.logger"
    assert payload["attributes"]["code.lineno"] == 10
    assert "timestamp" in payload
    assert "time_unix_nano" in payload
    assert "observed_time_unix_nano" in payload
    assert "exception" not in payload


def test_json_formatter_formats_record_with_exception():
    formatter = logger_module.JsonFormatter()

    try:
        _raise_value_error()
    except ValueError:
        exc_info = sys.exc_info()

    record = logging.LogRecord(
        name="test.logger",
        level=logging.ERROR,
        pathname=__file__,
        lineno=20,
        msg="failure",
        args=(),
        exc_info=exc_info,
    )

    payload = json.loads(formatter.format(record))

    assert payload["level"] == "ERROR"
    assert payload["message"] == "failure"
    assert payload["severity_text"] == "ERROR"
    assert payload["severity_number"] == 17
    assert "ValueError: boom" in payload["exception"]
    assert payload["attributes"]["exception.type"] == "ValueError"
    assert payload["attributes"]["exception.message"] == "boom"
    assert "ValueError: boom" in payload["attributes"]["exception.stacktrace"]


def test_setup_logging_reconfigures_uvicorn_loggers(monkeypatch: pytest.MonkeyPatch):
    logger_names = [
        logger_module.app_settings.app_name,
        "uvicorn",
        "uvicorn.access",
        "uvicorn.error",
    ]
    otel_handler = logging.NullHandler()
    monkeypatch.setattr(logger_module, "get_otel_log_handler", lambda: otel_handler)

    root = logging.getLogger()
    monkeypatch.setattr(root, "handlers", [logging.NullHandler()])
    monkeypatch.setattr(root, "level", logging.WARNING)

    for logger_name in logger_names:
        log = logging.getLogger(logger_name)
        monkeypatch.setattr(
            log, "handlers", [logging.NullHandler(), logging.NullHandler()]
        )
        monkeypatch.setattr(log, "level", logging.WARNING)
        monkeypatch.setattr(log, "propagate", True)

    logger_module.setup_logging()

    assert root.handlers == [otel_handler]
    assert root.level == logging.INFO
    assert root.disabled is False

    for logger_name in logger_names:
        log = logging.getLogger(logger_name)
        assert log.handlers == [otel_handler]
        assert log.level == logging.INFO
        assert log.disabled is False
        assert log.propagate is False


def test_logfire_handler_preserves_json_formatter_payload(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(formatter_module.time, "time_ns", lambda: 123456789)
    record = logging.LogRecord(
        name="test.logger",
        level=logging.WARNING,
        pathname=__file__,
        lineno=30,
        msg="hello %s",
        args=("logfire",),
        exc_info=None,
    )
    record.component = "unit-test"

    handler = JsonPayloadLogfireLoggingHandler()

    attributes = handler.fill_attributes(record)

    assert attributes[JSON_LOG_ATTRIBUTE] == logger_module.formatter.format(record)


def test_logfire_handler_writes_otel_json_to_stdout(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(formatter_module.time, "time_ns", lambda: 123456789)
    record = logging.LogRecord(
        name="test.logger",
        level=logging.INFO,
        pathname=__file__,
        lineno=40,
        msg="stdout %s",
        args=("otel",),
        exc_info=None,
    )
    record.component = "unit-test"
    stream = StringIO()
    handler = JsonPayloadLogfireLoggingHandler(stream=stream)
    logfire_instance = Mock()
    handler.logfire_instance = logfire_instance

    handler.emit(record)

    stdout_payload = stream.getvalue().strip()
    exported_attributes = logfire_instance.log.call_args.kwargs["attributes"]
    parsed = json.loads(stdout_payload)

    assert stdout_payload == exported_attributes[JSON_LOG_ATTRIBUTE]
    assert parsed["message"] == "stdout otel"
    assert parsed["severity_text"] == "INFO"
    assert parsed["severity_number"] == 9
    assert parsed["attributes"]["component"] == "unit-test"


def test_json_formatter_stringifies_non_json_extra_attributes() -> None:
    formatter = logger_module.JsonFormatter()
    record = logging.LogRecord(
        name="test.logger",
        level=logging.INFO,
        pathname=__file__,
        lineno=45,
        msg="extra payload",
        args=(),
        exc_info=None,
    )
    record.request_id = UUID("00000000-0000-0000-0000-000000000001")
    record.started_at = datetime(2026, 6, 21, tzinfo=UTC)
    record.context = {"items": {1, 2}}

    payload = json.loads(formatter.format(record))

    assert payload["attributes"]["request_id"] == (
        "00000000-0000-0000-0000-000000000001"
    )
    assert payload["attributes"]["started_at"] == "2026-06-21 00:00:00+00:00"
    assert sorted(payload["attributes"]["context"]["items"]) == [1, 2]


def test_logfire_handler_filters_health_endpoint_access_logs() -> None:
    record = logging.LogRecord(
        name="uvicorn.access",
        level=logging.INFO,
        pathname=__file__,
        lineno=50,
        msg='%s - "%s %s HTTP/%s" %d',
        args=("127.0.0.1:50000", "GET", "/health/db", "1.1", 200),
        exc_info=None,
    )
    stream = StringIO()
    handler = JsonPayloadLogfireLoggingHandler(stream=stream)
    logfire_instance = Mock()
    handler.logfire_instance = logfire_instance

    handled = handler.handle(record)

    assert handled is False
    assert stream.getvalue() == ""
    logfire_instance.log.assert_not_called()


@pytest.mark.parametrize(
    ("wrapper", "method_name"),
    [
        ("info", "info"),
        ("error", "error"),
        ("warning", "warning"),
        ("debug", "debug"),
    ],
)
def test_log_wrappers_delegate(monkeypatch, wrapper, method_name):
    method = Mock()
    monkeypatch.setattr(logger_module.logger, method_name, method)

    getattr(logger_module, wrapper)("message %s", "value")

    method.assert_called_once_with("message %s", "value")
