from uuid import UUID

from app.exceptions.base import BaseError


class NoEntityFoundError(BaseError):
    def __init__(self, entity_id: UUID) -> None:
        super().__init__(
            message=f"Entity '{entity_id}' not found",
            status_code=404,
            title="Not Found",
        )


class AuthenticationError(BaseError):
    def __init__(self) -> None:
        super().__init__(
            message="Unauthorized",
            status_code=401,
            title="Unauthorized",
            headers={"WWW-Authenticate": "Bearer"},
        )


class DatabaseUnavailableError(BaseError):
    def __init__(self) -> None:
        super().__init__(
            message="The database is unavailable.",
            status_code=503,
            title="Service Unavailable",
        )


class PetClinicNotFoundError(BaseError):
    def __init__(self, resource: str, resource_id: int | None = None) -> None:
        subject = resource if resource_id is None else f"{resource} '{resource_id}'"
        super().__init__(
            message=f"{subject} not found",
            status_code=404,
            title="Not Found",
        )


class PetClinicConflictError(BaseError):
    def __init__(self, message: str) -> None:
        super().__init__(message=message, status_code=409, title="Conflict")
