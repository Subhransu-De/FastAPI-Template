import logging
from unittest.mock import Mock

import pytest

from app.logger import configuration
from app.logger.handlers import get_logfire_handler

pytestmark = pytest.mark.unit


def test_setup_logging_reconfigures_uvicorn_loggers(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    logger_names = ["uvicorn", "uvicorn.access", "uvicorn.error"]
    otel_handler = logging.NullHandler()

    root = logging.getLogger()
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

    assert root.handlers == [otel_handler]
    assert root.level == logging.INFO
    assert root.disabled is False

    for logger_name in logger_names:
        logger = logging.getLogger(logger_name)
        assert logger.handlers == [otel_handler]
        assert logger.level == logging.INFO
        assert logger.disabled is False
        assert logger.propagate is False


def _access_record(path: str) -> logging.LogRecord:
    return logging.LogRecord(
        name="uvicorn.access",
        level=logging.INFO,
        pathname=__file__,
        lineno=50,
        msg='%s - "%s %s HTTP/%s" %d',
        args=("127.0.0.1:50000", "GET", path, "1.1", 200),
        exc_info=None,
    )


@pytest.mark.parametrize("path", ["/health", "/health/ready", "/health?probe=1"])
def test_logfire_handler_filters_health_endpoint_access_logs(path: str) -> None:
    handler = get_logfire_handler()
    logfire_instance = Mock()
    handler.logfire_instance = logfire_instance

    handled = handler.handle(_access_record(path))

    assert handled is False
    logfire_instance.log.assert_not_called()


def test_logfire_handler_keeps_other_access_logs() -> None:
    handler = get_logfire_handler()
    handler.logfire_instance = Mock()

    assert handler.handle(_access_record("/entities/")) is not False
