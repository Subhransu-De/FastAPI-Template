import logging

import logfire

from app.logger.filters import HealthEndpointFilter

LOG_LEVEL = logging.INFO

__all__ = [
    "LOG_LEVEL",
    "get_logfire_handler",
]

def get_logfire_handler() -> logfire.LogfireLoggingHandler:
    handler = logfire.LogfireLoggingHandler(
        level=LOG_LEVEL,
        fallback=logging.NullHandler(),
    )
    handler.addFilter(HealthEndpointFilter())
    return handler
