import logging
from unittest.mock import Mock

import logfire
import pytest

from app.logger import configuration
from app.logger.handlers import get_logfire_handler

pytestmark = pytest.mark.unit


def test_setup_logging_reconfigures_uvicorn_loggers(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    logger_names = ["uvicorn", "uvicorn.access", "uvicorn.error"]
    otel_handler = logging.NullHandler()
    configure_otel = Mock()

    root = logging.getLogger()
    monkeypatch.setattr(configuration, "configure_otel", configure_otel)
    monkeypatch.setattr(root, "handlers", [logging.NullHandler()])
    monkeypatch.setattr(root, "level", logging.WARNING)

    for logger_name in logger_names:
        logger = logging.getLogger(logger_name)
        monkeypatch.setattr(
            logger,
            "handlers",
            [logging.NullHandler(), logging.NullHandler()],
        )
        monkeypatch.setattr(logger, "level", logging.WARNING)
        monkeypatch.setattr(logger, "propagate", True)

    configuration.setup_logging(otel_handler_factory=lambda: otel_handler)

    configure_otel.assert_not_called()
    assert root.handlers == [otel_handler]
    assert root.level == logging.INFO
    assert root.disabled is False

    for logger_name in logger_names:
        logger = logging.getLogger(logger_name)
        assert logger.handlers == [otel_handler]
        assert logger.level == logging.INFO
        assert logger.disabled is False
        assert logger.propagate is False


def test_setup_logging_configures_otel_for_default_handler(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    configure_otel = Mock()
    configure_logger = Mock()
    monkeypatch.setattr(configuration, "configure_otel", configure_otel)
    monkeypatch.setattr(configuration, "configure_logger", configure_logger)

    configuration.setup_logging()

    configure_otel.assert_called_once_with()


def test_logfire_handler_uses_stock_handler_with_null_fallback() -> None:
    handler = get_logfire_handler()

    assert type(handler) is logfire.LogfireLoggingHandler
    assert isinstance(handler.fallback, logging.NullHandler)


def test_logfire_handler_filters_health_endpoint_access_logs() -> None:
    record = logging.LogRecord(
        name="uvicorn.access",
        level=logging.INFO,
        pathname=__file__,
        lineno=50,
        msg='%s - "%s %s HTTP/%s" %d',
        args=("127.0.0.1:50000", "GET", "/health", "1.1", 200),
        exc_info=None,
    )
    handler = get_logfire_handler()
    logfire_instance = Mock()
    handler.logfire_instance = logfire_instance

    handled = handler.handle(record)

    assert handled is False
    logfire_instance.log.assert_not_called()
