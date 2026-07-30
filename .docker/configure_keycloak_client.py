# ruff: noqa: INP001
"""Configure the Keycloak client for the current Compose project."""

import logging
import os
import time
from typing import Any
from urllib.parse import quote

import httpx

logger = logging.getLogger(__name__)

_KEYCLOAK_URL = "http://localhost:8080"
_AUTH_ATTEMPTS = 10
_AUTH_RETRY_SECONDS = 2.0
_RESOURCE_NAME = "FastAPI API"
_MANAGED_ROLE_PREFIXES = ("permission:", "role:")
_ROLE_PAGE_SIZE = 100
_PERMISSION_ROLES = (
    "permission:entity:list",
    "permission:entity:read",
    "permission:entity:create",
    "permission:entity:update",
    "permission:entity:delete",
    "permission:role:list",
    "permission:role:assign",
    "permission:role:remove",
)
_BUSINESS_ROLES = {
    "role:entity-reader": (
        "permission:entity:list",
        "permission:entity:read",
    ),
    "role:entity-editor": (
        "permission:entity:list",
        "permission:entity:read",
        "permission:entity:create",
        "permission:entity:update",
    ),
    "role:entity-admin": (
        "permission:entity:list",
        "permission:entity:read",
        "permission:entity:create",
        "permission:entity:update",
        "permission:entity:delete",
    ),
    "role:role-admin": (
        "permission:role:list",
        "permission:role:assign",
        "permission:role:remove",
    ),
}


def _get_admin_token(client: httpx.Client, password: str) -> str:
    last_error: Exception | None = None
    for _ in range(_AUTH_ATTEMPTS):
        try:
            response = client.post(
                "/realms/master/protocol/openid-connect/token",
                data={
                    "grant_type": "password",
                    "client_id": "admin-cli",
                    "username": "admin",
                    "password": password,
                },
            )
            response.raise_for_status()
            return str(response.json()["access_token"])
        except (httpx.HTTPError, KeyError) as exc:
            last_error = exc
            time.sleep(_AUTH_RETRY_SECONDS)

    message = f"Could not authenticate to Keycloak after {_AUTH_ATTEMPTS} attempts"
    raise RuntimeError(message) from last_error


def _get_keycloak_client_representation(
    client: httpx.Client,
    realm: str,
    client_id: str,
) -> dict[str, Any]:
    response = client.get(
        f"/admin/realms/{realm}/clients",
        params={"clientId": client_id},
    )
    response.raise_for_status()
    matches = response.json()
    if len(matches) != 1:
        message = f"Expected one '{client_id}' client in realm '{realm}'"
        raise RuntimeError(message)
    return dict(matches[0])


def _ensure_client_role(
    client: httpx.Client,
    realm: str,
    client_uuid: str,
    role_name: str,
) -> dict[str, Any]:
    role_path = quote(role_name, safe="")
    response = client.get(
        f"/admin/realms/{realm}/clients/{client_uuid}/roles/{role_path}"
    )
    if response.status_code == httpx.codes.NOT_FOUND:
        response = client.post(
            f"/admin/realms/{realm}/clients/{client_uuid}/roles",
            json={"name": role_name},
        )
        response.raise_for_status()
        response = client.get(
            f"/admin/realms/{realm}/clients/{client_uuid}/roles/{role_path}"
        )
    response.raise_for_status()
    return dict(response.json())


def _configure_roles(
    client: httpx.Client,
    realm: str,
    client_uuid: str,
) -> dict[str, dict[str, Any]]:
    managed_role_names = (*_PERMISSION_ROLES, *_BUSINESS_ROLES)
    _remove_stale_managed_roles(
        client,
        realm,
        client_uuid,
        set(managed_role_names),
    )
    roles = {
        name: _ensure_client_role(client, realm, client_uuid, name)
        for name in managed_role_names
    }
    for business_role, permission_roles in _BUSINESS_ROLES.items():
        _reconcile_role_composites(
            client,
            realm,
            client_uuid,
            roles[business_role],
            [roles[name] for name in permission_roles],
        )
    return roles


def _remove_stale_managed_roles(
    client: httpx.Client,
    realm: str,
    client_uuid: str,
    desired_names: set[str],
) -> None:
    roles_path = f"/admin/realms/{realm}/clients/{client_uuid}/roles"
    first = 0
    existing_roles: list[dict[str, Any]] = []
    while True:
        response = client.get(
            roles_path,
            params={
                "briefRepresentation": "true",
                "first": first,
                "max": _ROLE_PAGE_SIZE,
            },
        )
        response.raise_for_status()
        roles = response.json()
        existing_roles.extend(roles)
        if len(roles) < _ROLE_PAGE_SIZE:
            break
        first += _ROLE_PAGE_SIZE
    for role in existing_roles:
        role_name = str(role.get("name", ""))
        if (
            role_name.startswith(_MANAGED_ROLE_PREFIXES)
            and role_name not in desired_names
        ):
            response = client.delete(f"{roles_path}/{quote(role_name, safe='')}")
            response.raise_for_status()


def _reconcile_role_composites(
    client: httpx.Client,
    realm: str,
    client_uuid: str,
    business_role: dict[str, Any],
    desired_permissions: list[dict[str, Any]],
) -> None:
    composites_path = (
        f"/admin/realms/{realm}/roles-by-id/{business_role['id']}/composites"
    )
    response = client.get(f"{composites_path}/clients/{client_uuid}")
    response.raise_for_status()
    desired_ids = {permission["id"] for permission in desired_permissions}
    stale_permissions = [
        composite
        for composite in response.json()
        if str(composite.get("name", "")).startswith("permission:")
        and composite.get("id") not in desired_ids
    ]
    if stale_permissions:
        response = client.request(
            "DELETE",
            composites_path,
            json=stale_permissions,
        )
        response.raise_for_status()
    if desired_permissions:
        response = client.post(composites_path, json=desired_permissions)
        response.raise_for_status()


def _configure_service_account(
    client: httpx.Client,
    realm: str,
    client_uuid: str,
) -> None:
    service_account = client.get(
        f"/admin/realms/{realm}/clients/{client_uuid}/service-account-user"
    )
    service_account.raise_for_status()
    realm_management = _get_keycloak_client_representation(
        client,
        realm,
        "realm-management",
    )
    role_representations: list[dict[str, Any]] = []
    for role_name in ("manage-users", "view-users", "view-clients"):
        response = client.get(
            f"/admin/realms/{realm}/clients/{realm_management['id']}/roles/{role_name}"
        )
        response.raise_for_status()
        role_representations.append(dict(response.json()))
    response = client.post(
        (
            f"/admin/realms/{realm}/users/{service_account.json()['id']}/"
            f"role-mappings/clients/{realm_management['id']}"
        ),
        json=role_representations,
    )
    response.raise_for_status()


def _find_named(items: list[dict[str, Any]], name: str) -> dict[str, Any] | None:
    return next((item for item in items if item.get("name") == name), None)


def _ensure_authorization_scope(
    client: httpx.Client,
    authz_base: str,
    scope_name: str,
) -> dict[str, Any]:
    scopes = client.get(f"{authz_base}/scope")
    scopes.raise_for_status()
    if scope := _find_named(scopes.json(), scope_name):
        return scope
    response = client.post(f"{authz_base}/scope", json={"name": scope_name})
    response.raise_for_status()
    scopes = client.get(f"{authz_base}/scope")
    scopes.raise_for_status()
    return next(item for item in scopes.json() if item["name"] == scope_name)


def _ensure_authorization_resource(
    client: httpx.Client,
    authz_base: str,
    scopes: list[dict[str, Any]],
) -> dict[str, Any]:
    resources = client.get(f"{authz_base}/resource")
    resources.raise_for_status()
    if resource := _find_named(resources.json(), _RESOURCE_NAME):
        response = client.get(f"{authz_base}/resource/{resource['_id']}")
        response.raise_for_status()
        representation = dict(response.json())
        representation["scopes"] = [
            {"id": scope["id"], "name": scope["name"]} for scope in scopes
        ]
        response = client.put(
            f"{authz_base}/resource/{resource['_id']}",
            json=representation,
        )
        response.raise_for_status()
        return representation
    response = client.post(
        f"{authz_base}/resource",
        json={
            "name": _RESOURCE_NAME,
            "displayName": _RESOURCE_NAME,
            "type": "urn:fastapi-template:resources:api",
            "ownerManagedAccess": False,
            "scopes": [{"id": scope["id"], "name": scope["name"]} for scope in scopes],
        },
    )
    response.raise_for_status()
    resources = client.get(f"{authz_base}/resource")
    resources.raise_for_status()
    return next(item for item in resources.json() if item["name"] == _RESOURCE_NAME)


def _ensure_role_policy(
    client: httpx.Client,
    authz_base: str,
    permission_role: dict[str, Any],
) -> dict[str, Any]:
    role_name = str(permission_role["name"])
    policy_name = f"{role_name} policy"
    payload = {
        "name": policy_name,
        "description": f"Checks the current {role_name} role mapping",
        "type": "role",
        "logic": "POSITIVE",
        "decisionStrategy": "UNANIMOUS",
        "roles": [{"id": permission_role["id"], "required": True}],
        "fetchRoles": True,
    }
    policies = client.get(f"{authz_base}/policy")
    policies.raise_for_status()
    policy = _find_named(policies.json(), policy_name)
    if policy is None:
        response = client.post(f"{authz_base}/policy/role", json=payload)
        response.raise_for_status()
    else:
        response = client.put(
            f"{authz_base}/policy/role/{policy['id']}",
            json=payload,
        )
        response.raise_for_status()
    policies = client.get(f"{authz_base}/policy")
    policies.raise_for_status()
    return next(item for item in policies.json() if item["name"] == policy_name)


def _ensure_scope_permission(
    client: httpx.Client,
    authz_base: str,
    resource: dict[str, Any],
    scope: dict[str, Any],
    policy: dict[str, Any],
) -> None:
    permission_name = f"{scope['name']} permission"
    payload = {
        "name": permission_name,
        "description": f"Protects the {scope['name']} API scope",
        "type": "scope",
        "logic": "POSITIVE",
        "decisionStrategy": "UNANIMOUS",
        "resources": [resource["_id"]],
        "scopes": [scope["id"]],
        "policies": [policy["id"]],
    }
    permissions = client.get(f"{authz_base}/permission")
    permissions.raise_for_status()
    permission = _find_named(permissions.json(), permission_name)
    if permission is None:
        response = client.post(f"{authz_base}/permission/scope", json=payload)
    else:
        response = client.put(
            f"{authz_base}/permission/scope/{permission['id']}",
            json=payload,
        )
    response.raise_for_status()


def _configure_authorization(
    client: httpx.Client,
    realm: str,
    client_uuid: str,
    roles: dict[str, dict[str, Any]],
) -> None:
    authz_base = f"/admin/realms/{realm}/clients/{client_uuid}/authz/resource-server"
    scopes = [
        _ensure_authorization_scope(
            client,
            authz_base,
            role_name.removeprefix("permission:"),
        )
        for role_name in _PERMISSION_ROLES
    ]
    resource = _ensure_authorization_resource(client, authz_base, scopes)
    for role_name, scope in zip(_PERMISSION_ROLES, scopes, strict=True):
        policy = _ensure_role_policy(client, authz_base, roles[role_name])
        _ensure_scope_permission(client, authz_base, resource, scope, policy)


def _assign_bootstrap_roles(
    client: httpx.Client,
    realm: str,
    client_uuid: str,
    username: str,
    roles: dict[str, dict[str, Any]],
) -> None:
    users = client.get(
        f"/admin/realms/{realm}/users",
        params={"username": username, "exact": "true"},
    )
    users.raise_for_status()
    matches = users.json()
    if len(matches) != 1:
        message = f"Expected one '{username}' user in realm '{realm}'"
        raise RuntimeError(message)
    response = client.post(
        (
            f"/admin/realms/{realm}/users/{matches[0]['id']}/"
            f"role-mappings/clients/{client_uuid}"
        ),
        json=[roles["role:entity-admin"], roles["role:role-admin"]],
    )
    response.raise_for_status()


def configure_keycloak_client() -> None:
    realm = os.environ["OIDC_REALM"]
    docs_client_id = os.environ["OIDC_DOCS_CLIENT_ID"]
    api_client_id = os.environ["OIDC_API_CLIENT_ID"]
    api_client_secret = os.environ["OIDC_API_CLIENT_SECRET"]
    app_public_url = os.environ["APP_PUBLIC_URL"].rstrip("/")

    with httpx.Client(base_url=_KEYCLOAK_URL, timeout=10.0) as client:
        token = _get_admin_token(client, os.environ["KEYCLOAK_ADMIN_PASSWORD"])
        client.headers["Authorization"] = f"Bearer {token}"
        representation = _get_keycloak_client_representation(
            client,
            realm,
            docs_client_id,
        )
        representation["redirectUris"] = [f"{app_public_url}/docs/oauth2-redirect"]
        representation["webOrigins"] = [app_public_url]
        response = client.put(
            f"/admin/realms/{realm}/clients/{representation['id']}",
            json=representation,
        )
        response.raise_for_status()

        api_representation = _get_keycloak_client_representation(
            client,
            realm,
            api_client_id,
        )
        api_representation["secret"] = api_client_secret
        api_representation["authorizationServicesEnabled"] = True
        api_representation["serviceAccountsEnabled"] = True
        response = client.put(
            f"/admin/realms/{realm}/clients/{api_representation['id']}",
            json=api_representation,
        )
        response.raise_for_status()
        roles = _configure_roles(
            client,
            realm,
            str(api_representation["id"]),
        )
        _configure_service_account(
            client,
            realm,
            str(api_representation["id"]),
        )
        _configure_authorization(
            client,
            realm,
            str(api_representation["id"]),
            roles,
        )
        if username := os.getenv("OIDC_BOOTSTRAP_USERNAME"):
            _assign_bootstrap_roles(
                client,
                realm,
                str(api_representation["id"]),
                username,
                roles,
            )

    logger.info(
        "Configured %s redirect URI: %s/docs/oauth2-redirect",
        docs_client_id,
        app_public_url,
    )
    logger.info("Configured roles and permissions for %s", api_client_id)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    configure_keycloak_client()
