from uuid import UUID as PyUUID
from uuid import uuid4

from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy.types import UUID


class Base(DeclarativeBase):
    id: Mapped[PyUUID] = mapped_column(UUID(), primary_key=True, default=uuid4)
