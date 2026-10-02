import logging

from app.telemetry import HEALTH_ENDPOINT_PATHS

_UVICORN_ACCESS_PATH_ARG_INDEX = 2

__all__ = ["HealthEndpointFilter"]


def _record_path(record: logging.LogRecord) -> str | None:
    args = record.args
    if isinstance(args, tuple) and len(args) > _UVICORN_ACCESS_PATH_ARG_INDEX:
        path = args[_UVICORN_ACCESS_PATH_ARG_INDEX]
        if isinstance(path, str):
            return path.split("?", maxsplit=1)[0]

    message = record.getMessage()
    for path in HEALTH_ENDPOINT_PATHS:
        if f" {path} " in message:
            return path

    return None


class HealthEndpointFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        if record.name != "uvicorn.access":
            return True

        return _record_path(record) not in HEALTH_ENDPOINT_PATHS
