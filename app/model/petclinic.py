from datetime import date

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Column,
    Date,
    ForeignKey,
    Identity,
    Index,
    Integer,
    String,
    Table,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

from app.model.base import Base


class PetClinicModel(DeclarativeBase):
    metadata = Base.metadata


vet_specialties = Table(
    "vet_specialties",
    PetClinicModel.metadata,
    Column(
        "vet_id",
        ForeignKey("vets.id", ondelete="CASCADE"),
        primary_key=True,
    ),
    Column(
        "specialty_id",
        ForeignKey("specialties.id", ondelete="RESTRICT"),
        primary_key=True,
    ),
    UniqueConstraint(
        "vet_id",
        "specialty_id",
        name="uq_vet_specialties_vet_specialty",
    ),
)


class Owner(PetClinicModel):
    __tablename__ = "owners"
    __table_args__ = (
        CheckConstraint(
            "telephone ~ '^[0-9]{10}$'",
            name="ck_owners_telephone_10_digits",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, Identity(), primary_key=True)
    first_name: Mapped[str] = mapped_column(String(30), nullable=False)
    last_name: Mapped[str] = mapped_column(String(30), nullable=False, index=True)
    address: Mapped[str] = mapped_column(String(255), nullable=False)
    city: Mapped[str] = mapped_column(String(80), nullable=False)
    telephone: Mapped[str] = mapped_column(String(10), nullable=False)
    pets: Mapped[list["Pet"]] = relationship(
        back_populates="owner",
        cascade="all, delete-orphan",
        passive_deletes=True,
        lazy="selectin",
        order_by=lambda: func.lower(Pet.name),
    )


class PetType(PetClinicModel):
    __tablename__ = "types"

    id: Mapped[int] = mapped_column(Integer, Identity(), primary_key=True)
    name: Mapped[str] = mapped_column(String(80), nullable=False)
    pets: Mapped[list["Pet"]] = relationship(back_populates="type", lazy="raise")


class Pet(PetClinicModel):
    __tablename__ = "pets"

    id: Mapped[int] = mapped_column(Integer, Identity(), primary_key=True)
    name: Mapped[str] = mapped_column(String(30), nullable=False, index=True)
    birth_date: Mapped[date] = mapped_column(Date, nullable=False)
    type_id: Mapped[int] = mapped_column(
        ForeignKey("types.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    owner_id: Mapped[int] = mapped_column(
        ForeignKey("owners.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    type: Mapped[PetType] = relationship(back_populates="pets", lazy="selectin")
    owner: Mapped[Owner] = relationship(back_populates="pets", lazy="raise")
    visits: Mapped[list["Visit"]] = relationship(
        back_populates="pet",
        cascade="all, delete-orphan",
        passive_deletes=True,
        lazy="selectin",
        order_by=lambda: Visit.date.desc(),  # noqa: PLW0108
    )


class Visit(PetClinicModel):
    __tablename__ = "visits"

    id: Mapped[int] = mapped_column(Integer, Identity(), primary_key=True)
    pet_id: Mapped[int] = mapped_column(
        ForeignKey("pets.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    date: Mapped[date] = mapped_column("visit_date", Date, nullable=False)
    description: Mapped[str] = mapped_column(String(255), nullable=False)
    pet: Mapped[Pet] = relationship(back_populates="visits", lazy="raise")


class Specialty(PetClinicModel):
    __tablename__ = "specialties"

    id: Mapped[int] = mapped_column(Integer, Identity(), primary_key=True)
    name: Mapped[str] = mapped_column(String(80), nullable=False)
    vets: Mapped[list["Vet"]] = relationship(
        secondary=vet_specialties,
        back_populates="specialties",
        lazy="raise",
    )


class Vet(PetClinicModel):
    __tablename__ = "vets"

    id: Mapped[int] = mapped_column(Integer, Identity(), primary_key=True)
    first_name: Mapped[str] = mapped_column(String(30), nullable=False)
    last_name: Mapped[str] = mapped_column(String(30), nullable=False, index=True)
    specialties: Mapped[list[Specialty]] = relationship(
        secondary=vet_specialties,
        back_populates="vets",
        lazy="selectin",
        order_by=lambda: func.lower(Specialty.name),
    )


class User(PetClinicModel):
    __tablename__ = "users"

    username: Mapped[str] = mapped_column(String(80), primary_key=True)
    password: Mapped[str] = mapped_column(String(255), nullable=False)
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    roles: Mapped[list["Role"]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
        lazy="selectin",
        order_by=lambda: Role.name,
    )


class Role(PetClinicModel):
    __tablename__ = "roles"
    __table_args__ = (
        UniqueConstraint("username", "role", name="uq_roles_username_role"),
    )

    id: Mapped[int] = mapped_column(Integer, Identity(), primary_key=True)
    username: Mapped[str] = mapped_column(
        ForeignKey("users.username", ondelete="CASCADE"),
        nullable=False,
    )
    name: Mapped[str] = mapped_column("role", String(80), nullable=False)
    user: Mapped[User] = relationship(back_populates="roles", lazy="raise")


Index("uq_types_name_ci", func.lower(PetType.name), unique=True)
Index("uq_specialties_name_ci", func.lower(Specialty.name), unique=True)
Index(
    "uq_pets_owner_name_ci",
    Pet.owner_id,
    func.lower(Pet.name),
    unique=True,
)
