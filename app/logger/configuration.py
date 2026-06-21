import logging
from collections.abc import Callable
from logging import Handler, Logger

from app.logger.handlers import LOG_LEVEL
from app.settings import app_settings
from app.telemetry import get_otel_log_handler

LogHandlerFactory = Callable[[], Handler]

__all__ = ["LogHandlerFactory", "configure_logger", "setup_logging"]

_CONFIGURED_LOGGER_NAMES = (
    app_settings.app_name,
    "uvicorn",
    "uvicorn.access",
    "uvicorn.error",
)


def _build_handlers(otel_handler_factory: LogHandlerFactory) -> list[Handler]:
    return [otel_handler_factory()]


def configure_logger(
    log: Logger,
    *,
    propagate: bool,
    otel_handler_factory: LogHandlerFactory,
) -> None:
    log.handlers = _build_handlers(otel_handler_factory)
    log.setLevel(LOG_LEVEL)
    log.disabled = False
    log.propagate = propagate


def setup_logging(
    otel_handler_factory: LogHandlerFactory = get_otel_log_handler,
) -> None:
    configure_logger(
        logging.getLogger(),
        propagate=True,
        otel_handler_factory=otel_handler_factory,
    )

    for logger_name in _CONFIGURED_LOGGER_NAMES:
        configure_logger(
            logging.getLogger(logger_name),
            propagate=False,
            otel_handler_factory=otel_handler_factory,
        )
