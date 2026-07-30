import asyncio
from collections.abc import Awaitable, Callable
from typing import Annotated, Protocol

import httpx
from fastapi import Depends, Request
from keycloak import KeycloakAdmin
from keycloak.exceptions import KeycloakError, KeycloakGetError

from app.auth.permissions import Permission
from app.exceptions import (
    AuthenticationError,
    AuthorizationError,
    AuthorizationServiceUnavailableError,
    RoleAlreadyAssignedError,
    RoleNotFoundError,
    UserNotFoundError,
)

_BUSINESS_ROLE_PREFIX = "role:"
_NOT_FOUND = 404


class PermissionAuthorizer(Protocol):
    async def authorize(
        self,
        access_token: str,
        permissions: tuple[Permission, ...],
    ) -> None: ...


class KeycloakPermissionAuthorizer:
    def __init__(
        self,
        client: httpx.AsyncClient,
        client_id: str,
        resource_name: str,
    ) -> None:
        self._client = client
        self._client_id = client_id
        self._resource_name = resource_name

    async def authorize(
        self,
        access_token: str,
        permissions: tuple[Permission, ...],
    ) -> None:
        requested = [
            f"{self._resource_name}#{permission.value}" for permission in permissions
        ]
        try:
            response = await self._client.post(
                "protocol/openid-connect/token",
                data={
                    "grant_type": "urn:ietf:params:oauth:grant-type:uma-ticket",
                    "audience": self._client_id,
                    "response_mode": "decision",
                    "permission": requested,
                },
                headers={"Authorization": f"Bearer {access_token}"},
            )
        except httpx.HTTPError as exc:
            raise AuthorizationServiceUnavailableError from exc

        if response.status_code == httpx.codes.UNAUTHORIZED:
            raise AuthenticationError
        if response.status_code == httpx.codes.FORBIDDEN:
            raise AuthorizationError
        try:
            response.raise_for_status()
            granted = response.json()["result"]
        except (httpx.HTTPError, KeyError, TypeError, ValueError) as exc:
            raise AuthorizationServiceUnavailableError from exc
        if granted is not True:
            raise AuthorizationError

    async def close(self) -> None:
        await self._client.aclose()


def require_permissions(
    *permissions: Permission,
) -> Callable[[Request], Awaitable[None]]:
    if not permissions:
        message = "At least one permission is required"
        raise ValueError(message)

    async def dependency(request: Request) -> None:
        access_token = getattr(request.state, "access_token", None)
        if not access_token:
            raise AuthenticationError
        authorizer: PermissionAuthorizer = request.app.state.permission_authorizer
        await authorizer.authorize(access_token, tuple(permissions))

    return dependency


class KeycloakRoleManager:
    def __init__(self, admin: KeycloakAdmin, client_id: str) -> None:
        self._admin = admin
        self._client_id = client_id
        self._client_uuid: str | None = None
        self._assignment_lock = asyncio.Lock()

    async def list_roles(self, user_id: str) -> list[str]:
        client_uuid = await self._get_client_uuid()
        try:
            await self._admin.a_get_user(user_id)
            roles = await self._admin.a_get_client_roles_of_user(
                user_id,
                client_uuid,
            )
        except KeycloakGetError as exc:
            self._raise_user_not_found(exc, user_id)
            raise AuthorizationServiceUnavailableError from exc
        except KeycloakError as exc:
            raise AuthorizationServiceUnavailableError from exc

        return sorted(
            role["name"]
            for role in roles
            if role.get("name", "").startswith(_BUSINESS_ROLE_PREFIX)
        )

    async def assign_role(self, user_id: str, role_name: str) -> None:
        self._validate_business_role(role_name)
        async with self._assignment_lock:
            client_uuid = await self._get_client_uuid()
            role = await self._get_role(client_uuid, role_name)
            try:
                await self._admin.a_get_user(user_id)
                assigned = await self._admin.a_get_client_roles_of_user(
                    user_id,
                    client_uuid,
                )
                if any(item.get("id") == role.get("id") for item in assigned):
                    raise RoleAlreadyAssignedError(role_name)
                await self._admin.a_assign_client_role(
                    user_id,
                    client_uuid,
                    [role],
                )
            except KeycloakGetError as exc:
                self._raise_user_not_found(exc, user_id)
                raise AuthorizationServiceUnavailableError from exc
            except KeycloakError as exc:
                raise AuthorizationServiceUnavailableError from exc

    async def remove_role(self, user_id: str, role_name: str) -> None:
        self._validate_business_role(role_name)
        client_uuid = await self._get_client_uuid()
        role = await self._get_role(client_uuid, role_name)
        try:
            await self._admin.a_get_user(user_id)
            await self._admin.a_delete_client_roles_of_user(
                user_id,
                client_uuid,
                [role],
            )
        except KeycloakGetError as exc:
            self._raise_user_not_found(exc, user_id)
            raise AuthorizationServiceUnavailableError from exc
        except KeycloakError as exc:
            raise AuthorizationServiceUnavailableError from exc

    async def _get_client_uuid(self) -> str:
        if self._client_uuid is not None:
            return self._client_uuid
        try:
            client_uuid = await self._admin.a_get_client_id(self._client_id)
        except KeycloakError as exc:
            raise AuthorizationServiceUnavailableError from exc
        if not client_uuid:
            raise AuthorizationServiceUnavailableError
        self._client_uuid = client_uuid
        return client_uuid

    async def _get_role(self, client_uuid: str, role_name: str) -> dict:
        try:
            return await self._admin.a_get_client_role(client_uuid, role_name)
        except KeycloakGetError as exc:
            if exc.response_code == _NOT_FOUND:
                raise RoleNotFoundError(role_name) from exc
            raise AuthorizationServiceUnavailableError from exc
        except KeycloakError as exc:
            raise AuthorizationServiceUnavailableError from exc

    @staticmethod
    def _validate_business_role(role_name: str) -> None:
        if not role_name.startswith(_BUSINESS_ROLE_PREFIX):
            raise RoleNotFoundError(role_name)

    @staticmethod
    def _raise_user_not_found(exc: KeycloakGetError, user_id: str) -> None:
        if exc.response_code == _NOT_FOUND:
            raise UserNotFoundError(user_id) from exc


def get_role_manager(request: Request) -> KeycloakRoleManager:
    return request.app.state.role_manager


RoleManagerDependency = Annotated[KeycloakRoleManager, Depends(get_role_manager)]


def split_keycloak_realm_url(realm_url: str) -> tuple[str, str]:
    marker = "/realms/"
    server_url, separator, realm_name = realm_url.rstrip("/").rpartition(marker)
    if not separator or not server_url or not realm_name or "/" in realm_name:
        message = f"Invalid Keycloak realm URL: {realm_url}"
        raise ValueError(message)
    return f"{server_url}/", realm_name


def create_keycloak_clients(
    *,
    realm_url: str,
    client_id: str,
    client_secret: str,
    resource_name: str,
    timeout_seconds: int,
) -> tuple[KeycloakPermissionAuthorizer, KeycloakRoleManager]:
    server_url, realm_name = split_keycloak_realm_url(realm_url)
    authorization_client = httpx.AsyncClient(
        base_url=realm_url.rstrip("/") + "/",
        timeout=timeout_seconds,
    )
    admin = KeycloakAdmin(
        server_url=server_url,
        realm_name=realm_name,
        client_id=client_id,
        client_secret_key=client_secret,
        grant_type="client_credentials",
        timeout=timeout_seconds,
    )
    return (
        KeycloakPermissionAuthorizer(
            authorization_client,
            client_id,
            resource_name,
        ),
        KeycloakRoleManager(admin, client_id),
    )
