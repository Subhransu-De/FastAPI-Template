import logging
import sys
from logging import Formatter, Handler
from typing import TextIO

import logfire

from app.logger.filters import HealthEndpointFilter
from app.logger.formatters import JsonFormatter

LOG_LEVEL = logging.INFO
JSON_LOG_ATTRIBUTE = "app.log.json"
_JSON_PAYLOAD_RECORD_ATTRIBUTE = "_app_json_log_payload"

__all__ = [
    "JSON_LOG_ATTRIBUTE",
    "LOG_LEVEL",
    "JsonPayloadLogfireLoggingHandler",
    "formatter",
    "get_logfire_handler",
]

formatter: Formatter = JsonFormatter()


def _json_payload(record: logging.LogRecord) -> str:
    payload = getattr(record, _JSON_PAYLOAD_RECORD_ATTRIBUTE, None)
    if isinstance(payload, str):
        return payload

    payload = formatter.format(record)
    setattr(record, _JSON_PAYLOAD_RECORD_ATTRIBUTE, payload)
    return payload


class JsonPayloadLogfireLoggingHandler(logfire.LogfireLoggingHandler):
    terminator = "\n"

    def __init__(
        self,
        level: int | str = LOG_LEVEL,
        *,
        stream: TextIO | None = None,
    ) -> None:
        super().__init__(level=level, fallback=logging.NullHandler())
        self.stream = stream or sys.stdout
        self.addFilter(HealthEndpointFilter())

    def fill_attributes(self, record: logging.LogRecord) -> dict[str, object]:
        attributes = super().fill_attributes(record)
        attributes[JSON_LOG_ATTRIBUTE] = _json_payload(record)
        return attributes

    def emit(self, record: logging.LogRecord) -> None:
        try:
            payload = _json_payload(record)
            super().emit(record)
            self.stream.write(payload + self.terminator)
            self.flush()
        except Exception:  # noqa: BLE001
            self.handleError(record)

    def flush(self) -> None:
        if hasattr(self.stream, "flush"):
            self.stream.flush()


def get_logfire_handler() -> Handler:
    return JsonPayloadLogfireLoggingHandler(level=LOG_LEVEL)
