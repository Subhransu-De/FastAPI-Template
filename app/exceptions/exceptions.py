from uuid import UUID

from app.exceptions.base import BaseError


class NoEntityFoundError(BaseError):
    def __init__(self, entity_id: UUID) -> None:
        super().__init__(
            message=f"Entity '{entity_id}' not found",
            status_code=404,
            title="Not Found",
        )
