import json
from pathlib import Path

import pytest

pytestmark = pytest.mark.unit


@pytest.mark.parametrize(
    "realm_path",
    [
        Path(".docker/realm-export.json"),
        Path(".docker/e2e-realm-export.json"),
    ],
)
def test_swagger_oidc_client_is_public_pkce_with_api_audience(
    realm_path: Path,
) -> None:
    realm = json.loads(realm_path.read_text(encoding="utf-8"))
    clients = {client["clientId"]: client for client in realm["clients"]}

    docs_client = clients["fastapi-docs"]
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
