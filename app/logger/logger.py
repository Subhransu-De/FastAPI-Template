import logging
from logging import Logger

from app.logger.configuration import setup_logging as _setup_logging
from app.logger.formatters import JsonFormatter
from app.logger.handlers import LOG_LEVEL, formatter
from app.settings import app_settings
from app.telemetry import get_otel_log_handler

__all__ = [
    "JsonFormatter",
    "debug",
    "error",
    "formatter",
    "info",
    "logger",
    "setup_logging",
    "warning",
]

logger: Logger = logging.getLogger(app_settings.app_name)
logger.setLevel(LOG_LEVEL)


def setup_logging() -> None:
    _setup_logging(otel_handler_factory=get_otel_log_handler)


def info(msg: str, *args: object) -> None:
    logger.info(msg, *args)


def error(msg: str, *args: object) -> None:
    logger.error(msg, *args)


def warning(msg: str, *args: object) -> None:
    logger.warning(msg, *args)


def debug(msg: str, *args: object) -> None:
    logger.debug(msg, *args)
