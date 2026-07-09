from app.exceptions.base import BaseError, base_exception_handler
from app.exceptions.exceptions import (
    AuthenticationError,
    DatabaseUnavailableError,
    NoEntityFoundError,
)

__all__: list[str] = [
    "AuthenticationError",
    "BaseError",
    "DatabaseUnavailableError",
    "NoEntityFoundError",
    "base_exception_handler",
]
