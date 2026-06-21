import logging

HEALTH_ENDPOINT_PATH = "/health/db"
_UVICORN_ACCESS_PATH_ARG_INDEX = 2

__all__ = ["HEALTH_ENDPOINT_PATH", "HealthEndpointFilter"]


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
