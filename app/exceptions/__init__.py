from app.exceptions.base import BaseError, base_exception_handler
from app.exceptions.exceptions import NoEntityFoundError

__all__: list[str] = [
    "BaseError",
    "NoEntityFoundError",
    "base_exception_handler",
]
