from fastapi import APIRouter, Depends

from app.auth import (
    Permission,
    RoleManagerDependency,
    require_permissions,
)
from app.io.authorization import (
    RoleAssignmentRequest,
    UserRoleResponse,
    UserRolesResponse,
)

route = APIRouter(prefix="/users/{user_id}/roles", tags=["roles"])


@route.get(
    "/",
    dependencies=[Depends(require_permissions(Permission.ROLE_LIST))],
)
async def list_user_roles(
    user_id: str,
    role_manager: RoleManagerDependency,
) -> UserRolesResponse:
    roles = await role_manager.list_roles(user_id)
    return UserRolesResponse(user_id=user_id, roles=roles)


@route.post(
    "/",
    status_code=201,
    dependencies=[Depends(require_permissions(Permission.ROLE_ASSIGN))],
)
async def assign_user_role(
    user_id: str,
    data: RoleAssignmentRequest,
    role_manager: RoleManagerDependency,
) -> UserRoleResponse:
    await role_manager.assign_role(user_id, data.role_name)
    return UserRoleResponse(user_id=user_id, role_name=data.role_name)


@route.delete(
    "/{role_name}",
    status_code=204,
    dependencies=[Depends(require_permissions(Permission.ROLE_REMOVE))],
)
async def remove_user_role(
    user_id: str,
    role_name: str,
    role_manager: RoleManagerDependency,
) -> None:
    await role_manager.remove_role(user_id, role_name)
