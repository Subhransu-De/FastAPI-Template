from uuid import UUID

from app.exceptions.base import BaseException


class NoEntityFoundException(BaseException):
    def __init__(self, id: UUID):
        super().__init__(
            message=f"Entity '{id}' not found",
            status_code=404,
            title="Not Found",
        )
