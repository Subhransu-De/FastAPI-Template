import json
import logging
import os
import sys
import threading
import time
from logging import Formatter, Handler, Logger
from typing import Any

from app.settings import app_settings
from app.telemetry import get_otel_log_handler

_STANDARD_LOG_RECORD_ATTRIBUTES = {
    "args",
    "asctime",
    "created",
    "exc_info",
    "exc_text",
    "filename",
    "funcName",
    "levelname",
    "levelno",
    "lineno",
    "message",
    "module",
    "msecs",
    "msg",
    "name",
    "pathname",
    "process",
    "processName",
    "relativeCreated",
    "stack_info",
    "thread",
    "threadName",
    "taskName",
}


class JsonFormatter(Formatter):
    def _severity_number(self, level: int) -> int:
        if level >= logging.CRITICAL:
            return 21
        if level >= logging.ERROR:
            return 17
        if level >= logging.WARNING:
            return 13
        if level >= logging.INFO:
            return 9
        if level >= logging.DEBUG:
            return 5
        return 1

    def _attributes(self, record: logging.LogRecord) -> dict[str, Any]:
        attributes: dict[str, Any] = {
            "logger.name": record.name,
            "code.filepath": record.pathname,
            "code.function": record.funcName,
            "code.lineno": record.lineno,
            "process.pid": os.getpid(),
            "thread.id": threading.get_ident(),
            "thread.name": record.threadName,
        }

        attributes.update(
            {
                key: value
                for key, value in record.__dict__.items()
                if key not in _STANDARD_LOG_RECORD_ATTRIBUTES
            }
        )

        if record.exc_info:
            exception = record.exc_info[1]
            attributes["exception.type"] = type(exception).__name__
            attributes["exception.message"] = str(exception)
            attributes["exception.stacktrace"] = self.formatException(record.exc_info)

        return attributes

    def format(self, record: logging.LogRecord) -> str:
        attributes = self._attributes(record)
        log_object: dict[str, Any] = {
            "time_unix_nano": int(record.created * 1_000_000_000),
            "observed_time_unix_nano": time.time_ns(),
            "severity_text": record.levelname,
            "severity_number": self._severity_number(record.levelno),
            "body": record.getMessage(),
            "resource": {
                "service.name": app_settings.app_name,
            },
            "scope": {
                "name": record.name,
            },
            "attributes": attributes,
            "timestamp": self.formatTime(record, self.datefmt),
            "name": record.name,
            "level": record.levelname,
            "message": record.getMessage(),
        }
        if record.exc_info:
            log_object["exception"] = attributes["exception.stacktrace"]
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
