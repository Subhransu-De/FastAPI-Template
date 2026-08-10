import logging
from collections.abc import Callable
from logging import Handler, Logger

import logfire

from app.observability.configuration import configure_observability

LOG_LEVEL = logging.INFO
HEALTH_ENDPOINT_PATH = "/health"
_UVICORN_ACCESS_PATH_ARG_INDEX = 2
_CONFIGURED_LOGGER_NAMES = (
    "uvicorn",
    "uvicorn.access",
    "uvicorn.error",
)

LogHandlerFactory = Callable[[], Handler]


def _record_path(record: logging.LogRecord) -> str | None:
    args = record.args
    if isinstance(args, tuple) and len(args) > _UVICORN_ACCESS_PATH_ARG_INDEX:
        path = args[_UVICORN_ACCESS_PATH_ARG_INDEX]
        if isinstance(path, str):
            return path.split("?", maxsplit=1)[0]

    message = record.getMessage()
    marker = f" {HEALTH_ENDPOINT_PATH}"
    if marker in message:
        return HEALTH_ENDPOINT_PATH

    return None


class HealthEndpointFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        if record.name != "uvicorn.access":
            return True

        return _record_path(record) != HEALTH_ENDPOINT_PATH


def get_logfire_handler() -> logfire.LogfireLoggingHandler:
    handler = logfire.LogfireLoggingHandler(
        level=LOG_LEVEL,
        fallback=logging.NullHandler(),
    )
    handler.addFilter(HealthEndpointFilter())
    return handler


def _build_handlers(handler_factory: LogHandlerFactory) -> list[Handler]:
    return [handler_factory()]


def configure_logger(
    logger: Logger,
    *,
    propagate: bool,
    handler_factory: LogHandlerFactory,
) -> None:
    logger.handlers = _build_handlers(handler_factory)
    logger.setLevel(LOG_LEVEL)
    logger.disabled = False
    logger.propagate = propagate


def setup_logging(
    handler_factory: LogHandlerFactory = get_logfire_handler,
) -> None:
    if handler_factory is get_logfire_handler:
        configure_observability()
    configure_logger(
        logging.getLogger(),
        propagate=True,
        handler_factory=handler_factory,
    )

    for logger_name in _CONFIGURED_LOGGER_NAMES:
        configure_logger(
            logging.getLogger(logger_name),
            propagate=False,
            handler_factory=handler_factory,
        )
