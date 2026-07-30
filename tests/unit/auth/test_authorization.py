import asyncio
from unittest.mock import AsyncMock

import httpx
import pytest
from fastapi import FastAPI, Request
from keycloak.exceptions import KeycloakGetError

from app.auth.authorization import (
    KeycloakPermissionAuthorizer,
    KeycloakRoleManager,
    require_permissions,
    split_keycloak_realm_url,
)
from app.auth.permissions import Permission
from app.exceptions import (
    AuthenticationError,
    AuthorizationError,
    AuthorizationServiceUnavailableError,
    RoleAlreadyAssignedError,
    RoleNotFoundError,
    UserNotFoundError,
)

pytestmark = pytest.mark.unit

_TOKEN = "valid.jwt.token"  # noqa: S105
_TOKEN_ONE = "token-one"  # noqa: S105
_TOKEN_TWO = "token-two"  # noqa: S105


def _request(authorizer: AsyncMock, *, access_token: str | None = _TOKEN) -> Request:
    app = FastAPI()
    app.state.permission_authorizer = authorizer
    request = Request({"type": "http", "app": app})
    if access_token is not None:
        request.state.access_token = access_token
    return request


async def test_require_permissions_delegates_all_permissions() -> None:
    authorizer = AsyncMock()
    dependency = require_permissions(
        Permission.ENTITY_READ,
        Permission.ENTITY_LIST,
    )

    await dependency(_request(authorizer))

    authorizer.authorize.assert_awaited_once_with(
        _TOKEN,
        (Permission.ENTITY_READ, Permission.ENTITY_LIST),
    )


async def test_require_permissions_requires_authenticated_request() -> None:
    dependency = require_permissions(Permission.ENTITY_READ)

    with pytest.raises(AuthenticationError):
        await dependency(_request(AsyncMock(), access_token=None))


def test_require_permissions_rejects_empty_configuration() -> None:
    with pytest.raises(ValueError, match="At least one"):
        require_permissions()


async def test_keycloak_authorizer_allows_granted_permissions() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        assert request.headers["Authorization"] == f"Bearer {_TOKEN}"
        assert b"permission=FastAPI+API%23entity%3Aread" in request.content
        return httpx.Response(200, json={"result": True})

    client = httpx.AsyncClient(
        base_url="https://identity.example/realms/example/",
        transport=httpx.MockTransport(handler),
    )
    authorizer = KeycloakPermissionAuthorizer(
        client,
        "fastapi-client",
        "FastAPI API",
    )

    await authorizer.authorize(_TOKEN, (Permission.ENTITY_READ,))

    await authorizer.close()


@pytest.mark.parametrize(
    ("status_code", "body", "expected_error"),
    [
        (401, {}, AuthenticationError),
        (403, {}, AuthorizationError),
        (200, {"result": False}, AuthorizationError),
    ],
)
async def test_keycloak_authorizer_denies_ungranted_permissions(
    status_code: int,
    body: dict,
    expected_error: type[Exception],
) -> None:
    client = httpx.AsyncClient(
        base_url="https://identity.example/realms/example/",
        transport=httpx.MockTransport(
            lambda _request: httpx.Response(status_code, json=body)
        ),
    )
    authorizer = KeycloakPermissionAuthorizer(
        client,
        "fastapi-client",
        "FastAPI API",
    )

    with pytest.raises(expected_error):
        await authorizer.authorize(_TOKEN, (Permission.ENTITY_READ,))
    await authorizer.close()


async def test_keycloak_authorizer_fails_closed_when_keycloak_is_unavailable() -> None:
    def offline(request: httpx.Request) -> httpx.Response:
        message = "offline"
        raise httpx.ConnectError(message, request=request)

    client = httpx.AsyncClient(
        base_url="https://identity.example/realms/example/",
        transport=httpx.MockTransport(offline),
    )
    authorizer = KeycloakPermissionAuthorizer(
        client,
        "fastapi-client",
        "FastAPI API",
    )

    with pytest.raises(AuthorizationServiceUnavailableError):
        await authorizer.authorize(_TOKEN, (Permission.ENTITY_READ,))
    await authorizer.close()


async def test_concurrent_keycloak_decisions_keep_tokens_isolated() -> None:
    first_request_started = asyncio.Event()
    release_first_request = asyncio.Event()
    received_tokens: list[str] = []

    async def overlapping_handler(request: httpx.Request) -> httpx.Response:
        token = request.headers["Authorization"]
        received_tokens.append(token)
        if token == f"Bearer {_TOKEN_ONE}":
            first_request_started.set()
            await release_first_request.wait()
        else:
            await first_request_started.wait()
            release_first_request.set()
        return httpx.Response(200, json={"result": True})

    client = httpx.AsyncClient(
        base_url="https://identity.example/realms/example/",
        transport=httpx.MockTransport(overlapping_handler),
    )
    authorizer = KeycloakPermissionAuthorizer(
        client,
        "fastapi-client",
        "FastAPI API",
    )

    await asyncio.gather(
        authorizer.authorize(_TOKEN_ONE, (Permission.ENTITY_READ,)),
        authorizer.authorize(_TOKEN_TWO, (Permission.ENTITY_READ,)),
    )

    assert received_tokens == [
        f"Bearer {_TOKEN_ONE}",
        f"Bearer {_TOKEN_TWO}",
    ]
    await authorizer.close()


def _role_manager(admin: AsyncMock) -> KeycloakRoleManager:
    admin.a_get_client_id.return_value = "client-uuid"
    admin.a_get_user.return_value = {"id": "user-1"}
    admin.a_get_client_role.return_value = {
        "id": "role-uuid",
        "name": "role:entity-reader",
    }
    return KeycloakRoleManager(admin, "fastapi-client")


async def test_role_manager_lists_only_direct_business_roles() -> None:
    admin = AsyncMock()
    admin.a_get_client_roles_of_user.return_value = [
        {"name": "role:entity-reader"},
        {"name": "permission:entity:read"},
        {"name": "role:role-admin"},
    ]
    manager = _role_manager(admin)

    roles = await manager.list_roles("user-1")

    assert roles == ["role:entity-reader", "role:role-admin"]


async def test_role_manager_assigns_business_role() -> None:
    admin = AsyncMock()
    admin.a_get_client_roles_of_user.return_value = []
    manager = _role_manager(admin)

    await manager.assign_role("user-1", "role:entity-reader")

    admin.a_assign_client_role.assert_awaited_once_with(
        "user-1",
        "client-uuid",
        [{"id": "role-uuid", "name": "role:entity-reader"}],
    )


async def test_role_manager_rejects_duplicate_role_assignment() -> None:
    admin = AsyncMock()
    admin.a_get_client_roles_of_user.return_value = [
        {"id": "role-uuid", "name": "role:entity-reader"}
    ]
    manager = _role_manager(admin)

    with pytest.raises(RoleAlreadyAssignedError):
        await manager.assign_role("user-1", "role:entity-reader")

    admin.a_assign_client_role.assert_not_awaited()


async def test_role_manager_rejects_permission_role_assignment() -> None:
    manager = _role_manager(AsyncMock())

    with pytest.raises(RoleNotFoundError):
        await manager.assign_role("user-1", "permission:entity:read")


async def test_role_manager_reports_missing_user() -> None:
    admin = AsyncMock()
    admin.a_get_user.side_effect = KeycloakGetError(
        "missing",
        response_code=404,
    )
    manager = _role_manager(admin)

    with pytest.raises(UserNotFoundError):
        await manager.list_roles("missing-user")


async def test_role_manager_reports_missing_role() -> None:
    admin = AsyncMock()
    admin.a_get_client_role.side_effect = KeycloakGetError(
        "missing",
        response_code=404,
    )
    manager = _role_manager(admin)

    with pytest.raises(RoleNotFoundError):
        await manager.assign_role("user-1", "role:missing")


async def test_role_manager_removes_business_role() -> None:
    admin = AsyncMock()
    manager = _role_manager(admin)

    await manager.remove_role("user-1", "role:entity-reader")

    admin.a_delete_client_roles_of_user.assert_awaited_once_with(
        "user-1",
        "client-uuid",
        [{"id": "role-uuid", "name": "role:entity-reader"}],
    )


def test_split_keycloak_realm_url() -> None:
    assert split_keycloak_realm_url(
        "https://identity.example/realms/example/"
    ) == ("https://identity.example/", "example")


def test_split_keycloak_realm_url_rejects_non_keycloak_url() -> None:
    with pytest.raises(ValueError, match="Invalid Keycloak realm URL"):
        split_keycloak_realm_url("https://identity.example/issuer")
