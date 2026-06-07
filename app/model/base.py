from uuid import UUID as PYUUID
from uuid import uuid4

from pydantic import BaseModel
from sqlalchemy import MetaData
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy.types import UUID


class Base(DeclarativeBase):
    id: Mapped[PYUUID] = mapped_column(UUID(), primary_key=True, default=uuid4)

    metadata = MetaData(
        naming_convention={
            "ix": "ix_%(column_0_label)s",
            "uq": "uq_%(table_name)s_%(column_0_name)s",
            "ck": "ck_%(table_name)s_%(constraint_name)s",
            "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
            "pk": "pk_%(table_name)s",
        }
    )

    def apply_changes(self, data: BaseModel) -> None:
        for field, value in data.model_dump(exclude_unset=True).items():
            setattr(self, field, value)
