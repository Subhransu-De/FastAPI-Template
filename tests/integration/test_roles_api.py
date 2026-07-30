from typing import Any

import httpx
import pytest

from app.auth import Permission
from app.exceptions import RoleAlreadyAssignedError
from tests.integration.conftest import WithAuth

pytestmark = pytest.mark.integration


@WithAuth
async def test_list_user_roles(
    app_client: httpx.AsyncClient,
    role_manager: Any,
    permission_authorizer: Any,
) -> None:
    role_manager.list_roles.return_value = [
        "role:entity-reader",
        "role:role-admin",
    ]

    response = await app_client.get("/users/user-1/roles/")

    assert response.status_code == 200
    assert response.json() == {
        "user_id": "user-1",
        "roles": ["role:entity-reader", "role:role-admin"],
    }
    permission_authorizer.authorize.assert_awaited_once()
    assert permission_authorizer.authorize.await_args.args[1] == (
        Permission.ROLE_LIST,
    )


@WithAuth
async def test_assign_user_role(
    app_client: httpx.AsyncClient,
    role_manager: Any,
) -> None:
    response = await app_client.post(
        "/users/user-1/roles/",
        json={"role_name": "role:entity-reader"},
    )

    assert response.status_code == 201
    assert response.json() == {
        "user_id": "user-1",
        "role_name": "role:entity-reader",
    }
    role_manager.assign_role.assert_awaited_once_with(
        "user-1",
        "role:entity-reader",
    )


@WithAuth
async def test_duplicate_user_role_returns_conflict(
    app_client: httpx.AsyncClient,
    role_manager: Any,
) -> None:
    role_manager.assign_role.side_effect = RoleAlreadyAssignedError(
        "role:entity-reader"
    )

    response = await app_client.post(
        "/users/user-1/roles/",
        json={"role_name": "role:entity-reader"},
    )

    assert response.status_code == 409
    assert response.json()["title"] == "Conflict"
    assert response.json()["detail"] == (
        "Role 'role:entity-reader' is already assigned to the user."
    )


@WithAuth
async def test_remove_user_role(
    app_client: httpx.AsyncClient,
    role_manager: Any,
) -> None:
    response = await app_client.delete(
        "/users/user-1/roles/role:entity-reader"
    )

    assert response.status_code == 204
    role_manager.remove_role.assert_awaited_once_with(
        "user-1",
        "role:entity-reader",
    )
