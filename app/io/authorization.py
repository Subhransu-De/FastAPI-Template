from pydantic import BaseModel, ConfigDict, Field


class RoleAssignmentRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    role_name: str = Field(pattern=r"^role:[a-z0-9][a-z0-9:_-]*$")


class UserRoleResponse(BaseModel):
    user_id: str
    role_name: str


class UserRolesResponse(BaseModel):
    user_id: str
    roles: list[str]
