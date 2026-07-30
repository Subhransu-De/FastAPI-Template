from app.exceptions.base import BaseError, base_exception_handler
from app.exceptions.exceptions import (
    AuthenticationError,
    AuthorizationError,
    AuthorizationServiceUnavailableError,
    DatabaseUnavailableError,
    NoEntityFoundError,
    RoleAlreadyAssignedError,
    RoleNotFoundError,
    UserNotFoundError,
)

__all__: list[str] = [
    "AuthenticationError",
    "AuthorizationError",
    "AuthorizationServiceUnavailableError",
    "BaseError",
    "DatabaseUnavailableError",
    "NoEntityFoundError",
    "RoleAlreadyAssignedError",
    "RoleNotFoundError",
    "UserNotFoundError",
    "base_exception_handler",
]
