import json
import logging
import sys
from logging import Formatter, Logger


class JsonFormatter(Formatter):
    def format(self, record):
        log_object = {
            "timestamp": self.formatTime(record, self.datefmt),
            "name": record.name,
            "level": record.levelname,
            "message": record.getMessage(),
        }
        if record.exc_info:
            log_object["exception"] = self.formatException(record.exc_info)
        return json.dumps(log_object)


formatter: Formatter = JsonFormatter()

logger: Logger = logging.getLogger("fastapi_app")
logger.setLevel(logging.DEBUG)

console_handler = logging.StreamHandler(sys.stdout)
console_handler.setLevel(logging.DEBUG)
console_handler.setFormatter(formatter)

if not logger.handlers:
    logger.addHandler(console_handler)


def setup_logging():
    loggers = ["uvicorn", "uvicorn.access", "uvicorn.error"]
    for logger_name in loggers:
        log = logging.getLogger(logger_name)
        log.handlers = []

        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(formatter)
        log.addHandler(handler)

        log.setLevel(logging.INFO)

        log.propagate = False


def info(msg: str, *args, **kwargs):
    logger.info(msg, *args, **kwargs)


def error(msg: str, *args, **kwargs):
    logger.error(msg, *args, **kwargs)


def debug(msg: str, *args, **kwargs):
    logger.debug(msg, *args, **kwargs)
