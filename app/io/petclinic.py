import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator


def _to_camel(value: str) -> str:
    head, *tail = value.split("_")
    return head + "".join(part.capitalize() for part in tail)


class PetClinicSchema(BaseModel):
    model_config = ConfigDict(
        alias_generator=_to_camel,
        populate_by_name=True,
        from_attributes=True,
        serialize_by_alias=True,
    )


class NamedFields(PetClinicSchema):
    name: str = Field(min_length=1, max_length=80)


class PetTypeCreate(NamedFields):
    pass


class PetTypeUpdate(NamedFields):
    pass


class PetTypeResponse(NamedFields):
    id: int


class SpecialtyCreate(NamedFields):
    pass


class SpecialtyUpdate(NamedFields):
    pass


class SpecialtyResponse(NamedFields):
    id: int


class VisitNestedCreate(PetClinicSchema):
    date: datetime.date = Field(
        default_factory=lambda: datetime.datetime.now(datetime.UTC).date()
    )
    description: str = Field(min_length=1, max_length=255)


class VisitCreate(VisitNestedCreate):
    pet_id: int = Field(gt=0)


class VisitUpdate(PetClinicSchema):
    date: datetime.date
    description: str = Field(min_length=1, max_length=255)


class VisitResponse(PetClinicSchema):
    id: int
    date: datetime.date
    description: str
    pet_id: int


class PetFields(PetClinicSchema):
    name: str = Field(min_length=1, max_length=30)
    birth_date: datetime.date
    type: PetTypeResponse

    @field_validator("birth_date")
    @classmethod
    def validate_birth_date(cls, value: datetime.date) -> datetime.date:
        today = datetime.datetime.now(datetime.UTC).date()
        if value > today:
            message = "birthDate must not be in the future"
            raise ValueError(message)
        try:
            earliest = today.replace(year=today.year - 50)
        except ValueError:
            earliest = today.replace(year=today.year - 50, day=28)
        if value < earliest:
            message = "birthDate must be within the last 50 years"
            raise ValueError(message)
        return value


class PetCreate(PetFields):
    pass


class PetUpdate(PetFields):
    pass


class PetResponse(PetFields):
    id: int
    owner_id: int
    visits: list[VisitResponse] = Field(default_factory=list)


class OwnerFields(PetClinicSchema):
    first_name: str = Field(
        min_length=1,
        max_length=30,
        pattern=r"^[\p{L}]+([ '-][\p{L}]+){0,2}$",
    )
    last_name: str = Field(
        min_length=1,
        max_length=30,
        pattern=r"^[\p{L}]+([ '-][\p{L}]+){0,2}\.?$",
    )
    address: str = Field(min_length=1, max_length=255)
    city: str = Field(min_length=1, max_length=80)
    telephone: str = Field(pattern=r"^\d{10}$")


class OwnerCreate(OwnerFields):
    pass


class OwnerUpdate(OwnerFields):
    pass


class OwnerResponse(OwnerFields):
    id: int
    pets: list[PetResponse] = Field(default_factory=list)


class OwnerPage(PetClinicSchema):
    content: list[OwnerResponse]
    page: int
    size: int
    total_elements: int
    total_pages: int


class PetPage(PetClinicSchema):
    content: list[PetResponse]
    page: int
    size: int
    total_elements: int
    total_pages: int


class VetFields(PetClinicSchema):
    first_name: str = Field(
        min_length=1,
        max_length=30,
        pattern=r"^[\p{L}]+([ '-][\p{L}]+){0,2}$",
    )
    last_name: str = Field(
        min_length=1,
        max_length=30,
        pattern=r"^[\p{L}]+([ '-][\p{L}]+){0,2}\.?$",
    )
    specialties: list[SpecialtyResponse] = Field(default_factory=list)


class VetCreate(VetFields):
    pass


class VetUpdate(VetFields):
    pass


class VetResponse(VetFields):
    id: int


class RoleInput(PetClinicSchema):
    name: str = Field(min_length=1, max_length=80)


class RoleResponse(RoleInput):
    pass


class UserCreate(PetClinicSchema):
    username: str = Field(min_length=1, max_length=80)
    password: str = Field(min_length=8, max_length=255)
    enabled: bool = True
    roles: list[RoleInput] = Field(min_length=1)


class UserResponse(PetClinicSchema):
    username: str
    enabled: bool
    roles: list[RoleResponse]
