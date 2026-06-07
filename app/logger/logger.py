import json
import logging
import sys
from logging import Formatter, Handler, Logger

from app.settings import app_settings
from app.telemetry import get_otel_log_handler


class JsonFormatter(Formatter):
    def format(self, record: logging.LogRecord) -> str:
        log_object: dict = {
            "timestamp": self.formatTime(record, self.datefmt),
            "name": record.name,
            "level": record.levelname,
            "message": record.getMessage(),
        }
        if record.exc_info:
            log_object["exception"] = self.formatException(record.exc_info)
        return json.dumps(log_object)


formatter: Formatter = JsonFormatter()

logger: Logger = logging.getLogger(app_settings.app_name)
logger.setLevel(logging.INFO)


def _get_console_handler() -> Handler:
    handler: Handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(logging.INFO)
    handler.setFormatter(formatter)
    return handler


if not logger.handlers:
    logger.addHandler(_get_console_handler())


def _configure_logger(log: Logger, *, propagate: bool) -> None:
    log.handlers = [_get_console_handler(), get_otel_log_handler()]
    log.setLevel(logging.INFO)
    log.disabled = False
    log.propagate = propagate


def setup_logging() -> None:
    _configure_logger(logging.getLogger(), propagate=True)

    loggers = [app_settings.app_name, "uvicorn", "uvicorn.access", "uvicorn.error"]
    for logger_name in loggers:
        _configure_logger(logging.getLogger(logger_name), propagate=False)


def info(msg: str, *args: object) -> None:
    logger.info(msg, *args)


def error(msg: str, *args: object) -> None:
    logger.error(msg, *args)


def warning(msg: str, *args: object) -> None:
    logger.warning(msg, *args)


def debug(msg: str, *args: object) -> None:
    logger.debug(msg, *args)
