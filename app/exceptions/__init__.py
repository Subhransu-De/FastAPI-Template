from app.exceptions.base import BaseError, base_exception_handler
from app.exceptions.exceptions import AuthenticationError, NoEntityFoundError

__all__: list[str] = [
    "AuthenticationError",
    "BaseError",
    "NoEntityFoundError",
    "base_exception_handler",
]
