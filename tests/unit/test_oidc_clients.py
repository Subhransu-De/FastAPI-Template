import json
from pathlib import Path

import pytest

from app.auth import ENTITY_WRITE_ROLE

pytestmark = pytest.mark.unit

_REALM_PATHS = [
    Path(".docker/realm-export.json"),
    Path(".docker/e2e-realm-export.json"),
]


def _load_realm(realm_path: Path) -> dict[str, object]:
    realm = json.loads(realm_path.read_text(encoding="utf-8"))
    assert isinstance(realm, dict)
    return realm


@pytest.mark.parametrize("realm_path", _REALM_PATHS)
def test_swagger_oidc_client_is_public_pkce_with_api_audience(
    realm_path: Path,
) -> None:
    realm = _load_realm(realm_path)
    clients = realm["clients"]
    assert isinstance(clients, list)
    clients_by_id = {client["clientId"]: client for client in clients}

    docs_client = clients_by_id["fastapi-docs"]
    assert docs_client["publicClient"] is True
    assert docs_client["standardFlowEnabled"] is True
    assert docs_client["directAccessGrantsEnabled"] is False
    assert docs_client["attributes"]["pkce.code.challenge.method"] == "S256"
    assert "secret" not in docs_client
    mappers = {mapper["name"]: mapper for mapper in docs_client["protocolMappers"]}
    assert mappers["api-audience"]["config"]["included.client.audience"] == (
        "fastapi-client"
    )
    assert mappers["not-before"]["config"]["claim.name"] == "nbf"
    assert mappers["not-before"]["config"]["access.token.claim"] == "true"


@pytest.mark.parametrize("realm_path", _REALM_PATHS)
@pytest.mark.parametrize("client_id", ["fastapi-client", "fastapi-docs"])
def test_api_client_scopes_allow_only_the_entity_write_role(
    realm_path: Path,
    client_id: str,
) -> None:
    realm = _load_realm(realm_path)
    clients = realm["clients"]
    scope_mappings = realm["scopeMappings"]
    assert isinstance(clients, list)
    assert isinstance(scope_mappings, list)

    clients_by_id = {client["clientId"]: client for client in clients}
    assert clients_by_id[client_id]["fullScopeAllowed"] is False
    mapped_roles = {
        role
        for mapping in scope_mappings
        if mapping["client"] == client_id
        for role in mapping["roles"]
    }
    assert mapped_roles == {ENTITY_WRITE_ROLE}


@pytest.mark.parametrize("realm_path", _REALM_PATHS)
def test_realm_grants_the_entity_write_role_to_local_users(realm_path: Path) -> None:
    realm = _load_realm(realm_path)
    roles = realm["roles"]
    users = realm["users"]
    assert isinstance(roles, dict)
    assert isinstance(users, list)

    realm_roles = {role["name"] for role in roles["realm"]}
    assert ENTITY_WRITE_ROLE in realm_roles
    assert users
    for user in users:
        assert ENTITY_WRITE_ROLE in user["realmRoles"], user["username"]
