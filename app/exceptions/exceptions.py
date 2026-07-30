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


class AuthorizationError(BaseError):
    def __init__(self) -> None:
        super().__init__(
            message="Forbidden",
            status_code=403,
            title="Forbidden",
        )


class AuthorizationServiceUnavailableError(BaseError):
    def __init__(self) -> None:
        super().__init__(
            message="The authorization service is unavailable.",
            status_code=503,
            title="Service Unavailable",
        )


class RoleAlreadyAssignedError(BaseError):
    def __init__(self, role_name: str) -> None:
        super().__init__(
            message=f"Role '{role_name}' is already assigned to the user.",
            status_code=409,
            title="Conflict",
        )


class RoleNotFoundError(BaseError):
    def __init__(self, role_name: str) -> None:
        super().__init__(
            message=f"Role '{role_name}' was not found.",
            status_code=404,
            title="Not Found",
        )


class UserNotFoundError(BaseError):
    def __init__(self, user_id: str) -> None:
        super().__init__(
            message=f"User '{user_id}' was not found.",
            status_code=404,
            title="Not Found",
        )


class DatabaseUnavailableError(BaseError):
    def __init__(self) -> None:
        super().__init__(
            message="The database is unavailable.",
            status_code=503,
            title="Service Unavailable",
        )
