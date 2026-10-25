from enum import StrEnum
from typing import Annotated
from uuid import UUID

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field


class EntityOrderBy(StrEnum):
    NAME = "name"
    DESCRIPTION = "description"
    CREATED_AT = "created_at"
    UPDATED_AT = "updated_at"


class OrderDirection(StrEnum):
    ASC = "asc"
    DESC = "desc"


EntityName = Annotated[str, Field(min_length=1, max_length=255)]
EntityDescription = Annotated[str | None, Field(max_length=5000)]


class EntityCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: EntityName
    description: EntityDescription = None


class EntityUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: EntityName
    description: EntityDescription = None


class EntityResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    description: str | None
    created_at: AwareDatetime
    updated_at: AwareDatetime
