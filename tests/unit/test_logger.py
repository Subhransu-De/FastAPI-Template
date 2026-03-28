import json
import logging
import sys
from unittest.mock import Mock

import pytest

import app.logger.logger as logger_module

pytestmark = pytest.mark.unit


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
    assert "timestamp" in payload
    assert "exception" not in payload


def test_json_formatter_formats_record_with_exception():
    formatter = logger_module.JsonFormatter()

    try:
        raise ValueError("boom")
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
    assert "ValueError: boom" in payload["exception"]


def test_setup_logging_reconfigures_uvicorn_loggers():
    logger_names = ["uvicorn", "uvicorn.access", "uvicorn.error"]
    originals = {}

    for logger_name in logger_names:
        log = logging.getLogger(logger_name)
        originals[logger_name] = (list(log.handlers), log.level, log.propagate)
        log.handlers = [logging.NullHandler(), logging.NullHandler()]
        log.setLevel(logging.WARNING)
        log.propagate = True

    try:
        logger_module.setup_logging()

        for logger_name in logger_names:
            log = logging.getLogger(logger_name)
            assert len(log.handlers) == 1
            assert isinstance(log.handlers[0], logging.StreamHandler)
            assert log.handlers[0].formatter is logger_module.formatter
            assert log.level == logging.INFO
            assert log.propagate is False
    finally:
        for logger_name in logger_names:
            handlers, level, propagate = originals[logger_name]
            log = logging.getLogger(logger_name)
            log.handlers = handlers
            log.setLevel(level)
            log.propagate = propagate


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
