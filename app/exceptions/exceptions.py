from http import HTTPStatus
from uuid import UUID

from app.exceptions.base import BaseError


class NoEntityFoundError(BaseError):
    def __init__(self, entity_id: UUID) -> None:
        super().__init__(
            message=f"Entity '{entity_id}' not found",
            status_code=HTTPStatus.NOT_FOUND,
            title=HTTPStatus.NOT_FOUND.phrase,
        )


class AuthenticationError(BaseError):
    def __init__(self) -> None:
        super().__init__(
            message="Unauthorized",
            status_code=HTTPStatus.UNAUTHORIZED,
            title=HTTPStatus.UNAUTHORIZED.phrase,
            headers={"WWW-Authenticate": "Bearer"},
        )


class ForbiddenError(BaseError):
    def __init__(self, role: str) -> None:
        super().__init__(
            message=f"Role '{role}' is required",
            status_code=HTTPStatus.FORBIDDEN,
            title=HTTPStatus.FORBIDDEN.phrase,
        )


class DatabaseUnavailableError(BaseError):
    def __init__(self) -> None:
        super().__init__(
            message="The database is unavailable.",
            status_code=HTTPStatus.SERVICE_UNAVAILABLE,
            title=HTTPStatus.SERVICE_UNAVAILABLE.phrase,
        )


class MissingLifespanStateError(RuntimeError):
    def __init__(self, key: str) -> None:
        super().__init__(
            f"Lifespan state '{key}' is missing; the application lifespan did not run"
        )
