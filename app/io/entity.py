from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class EntityCreate(BaseModel):
    name: str
    description: str | None = None


class EntityUpdate(BaseModel):
    name: str | None = None
    description: str | None = None


class EntityResponse(BaseModel):
    id: UUID
    name: str
    description: str | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
