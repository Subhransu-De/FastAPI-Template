from app.exceptions.base import BaseError, base_exception_handler
from app.exceptions.exceptions import (
    AuthenticationError,
    DatabaseUnavailableError,
    NoEntityFoundError,
    PetClinicConflictError,
    PetClinicNotFoundError,
)

__all__: list[str] = [
    "AuthenticationError",
    "BaseError",
    "DatabaseUnavailableError",
    "NoEntityFoundError",
    "PetClinicConflictError",
    "PetClinicNotFoundError",
    "base_exception_handler",
]
