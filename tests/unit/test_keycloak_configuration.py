import json
import runpy
from pathlib import Path

import httpx
import pytest

pytestmark = pytest.mark.unit

_CONFIGURATION_SCRIPT = (
    Path(__file__).parents[2] / ".docker" / "configure_keycloak_client.py"
)


def test_role_reconciliation_removes_only_obsolete_managed_roles() -> None:
    requests: list[httpx.Request] = []
    roles = [
        {"id": "kept-id", "name": "role:entity-reader"},
        {"id": "old-role-id", "name": "role:legacy"},
        {"id": "old-permission-id", "name": "permission:entity:legacy"},
        {"id": "custom-id", "name": "custom:shared"},
    ]

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        if request.method == "GET":
            return httpx.Response(200, json=roles)
        return httpx.Response(204)

    namespace = runpy.run_path(str(_CONFIGURATION_SCRIPT))
    remove_stale_roles = namespace["_remove_stale_managed_roles"]
    with httpx.Client(
        base_url="https://identity.example",
        transport=httpx.MockTransport(handler),
    ) as client:
        remove_stale_roles(
            client,
            "example",
            "client-id",
            {"role:entity-reader"},
        )

    deleted_paths = [
        request.url.path for request in requests if request.method == "DELETE"
    ]
    assert deleted_paths == [
        "/admin/realms/example/clients/client-id/roles/role:legacy",
        "/admin/realms/example/clients/client-id/roles/permission:entity:legacy",
    ]


def test_business_role_composites_remove_only_stale_permissions() -> None:
    requests: list[httpx.Request] = []
    existing_composites = [
        {"id": "desired-id", "name": "permission:entity:read"},
        {"id": "stale-id", "name": "permission:entity:legacy"},
        {"id": "unrelated-id", "name": "custom:shared"},
    ]

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        if request.method == "GET":
            return httpx.Response(200, json=existing_composites)
        return httpx.Response(204)

    namespace = runpy.run_path(str(_CONFIGURATION_SCRIPT))
    reconcile_composites = namespace["_reconcile_role_composites"]
    desired_permissions = [{"id": "desired-id", "name": "permission:entity:read"}]
    with httpx.Client(
        base_url="https://identity.example",
        transport=httpx.MockTransport(handler),
    ) as client:
        reconcile_composites(
            client,
            "example",
            "client-id",
            {"id": "business-role-id", "name": "role:entity-reader"},
            desired_permissions,
        )

    assert [request.method for request in requests] == ["GET", "DELETE", "POST"]
    assert requests[0].url.path.endswith(
        "/roles-by-id/business-role-id/composites/clients/client-id"
    )
    assert json.loads(requests[1].content) == [existing_composites[1]]
    assert json.loads(requests[2].content) == desired_permissions


def test_existing_authorization_resource_receives_complete_scope_set() -> None:
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        if request.method == "GET" and request.url.path.endswith("/resource"):
            return httpx.Response(
                200,
                json=[{"_id": "resource-id", "name": "FastAPI API"}],
            )
        if request.method == "GET":
            return httpx.Response(
                200,
                json={
                    "_id": "resource-id",
                    "name": "FastAPI API",
                    "displayName": "Existing display name",
                    "scopes": [{"id": "old-scope", "name": "old"}],
                },
            )
        return httpx.Response(204)

    namespace = runpy.run_path(str(_CONFIGURATION_SCRIPT))
    ensure_resource = namespace["_ensure_authorization_resource"]
    scopes = [
        {"id": "read-scope", "name": "entity:read"},
        {"id": "write-scope", "name": "entity:update"},
    ]
    with httpx.Client(
        base_url="https://identity.example",
        transport=httpx.MockTransport(handler),
    ) as client:
        resource = ensure_resource(
            client,
            "/admin/realms/example/clients/client-id/authz/resource-server",
            scopes,
        )

    update_request = requests[-1]
    assert update_request.method == "PUT"
    assert update_request.url.path.endswith("/resource/resource-id")
    update = json.loads(update_request.content)
    assert update["displayName"] == "Existing display name"
    assert update["scopes"] == scopes
    assert resource == update
