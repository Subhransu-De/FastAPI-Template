from uuid import UUID as PYUUID
from uuid import uuid4

from sqlalchemy import Identity, Integer, MetaData
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy.types import UUID


class Base(DeclarativeBase):
    metadata = MetaData(
        naming_convention={
            "ix": "ix_%(column_0_label)s",
            "uq": "uq_%(table_name)s_%(column_0_name)s",
            "ck": "ck_%(table_name)s_%(constraint_name)s",
            "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
            "pk": "pk_%(table_name)s",
        }
    )


class UUIDPrimaryKey:
    id: Mapped[PYUUID] = mapped_column(UUID(), primary_key=True, default=uuid4)


class IntegerPrimaryKey:
    id: Mapped[int] = mapped_column(Integer(), Identity(), primary_key=True)
