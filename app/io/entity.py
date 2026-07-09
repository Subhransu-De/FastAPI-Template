from datetime import datetime
from enum import StrEnum
from uuid import UUID

from pydantic import BaseModel, Field


class EntityOrderBy(StrEnum):
    NAME = "name"
    DESCRIPTION = "description"
    CREATED_AT = "created_at"
    UPDATED_AT = "updated_at"


class OrderDirection(StrEnum):
    ASC = "asc"
    DESC = "desc"


class EntityCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: str | None = Field(None, max_length=5000)


class EntityUpdate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: str | None = Field(None, max_length=5000)


class EntityResponse(BaseModel):
    id: UUID
    name: str
    description: str | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
