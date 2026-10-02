from collections.abc import Callable
from typing import Any
from uuid import uuid4

import httpx
import pytest
from cryptography.hazmat.primitives.asymmetric.rsa import RSAPrivateKey

from tests.integration.conftest import (
    WithAuth,
    make_hs256_token_signed_with_public_key,
    make_test_token,
    make_unsigned_token,
)

pytestmark = pytest.mark.integration


def _assert_problem_details(
    response: httpx.Response,
    *,
    status_code: int,
    title: str,
) -> dict[str, Any]:
    assert response.status_code == status_code
    assert response.headers["content-type"] == "application/problem+json"
    body = response.json()
    assert body["title"] == title
    assert body["status"] == status_code
    assert body["type"].endswith("/openapi.json")
    assert body["instance"] == str(response.request.url)
    return body


def _assert_validation_problem(
    response: httpx.Response,
    *,
    expected_location: tuple[str, ...],
) -> None:
    body = _assert_problem_details(
        response,
        status_code=422,
        title="Unprocessable Content",
    )
    assert any(tuple(error["loc"]) == expected_location for error in body["detail"]), (
        body["detail"]
    )


def _assert_unauthorized(response: httpx.Response) -> None:
    assert response.status_code == 401
    assert response.headers["WWW-Authenticate"] == "Bearer"
    assert response.headers["content-type"] == "application/problem+json"
    assert response.json() == {
        "type": "https://testserver/openapi.json",
        "title": "Unauthorized",
        "status": 401,
        "detail": "Unauthorized",
        "instance": str(response.request.url),
    }


async def test_entity_routes_require_bearer_authorization(
    app_client: httpx.AsyncClient,
) -> None:
    response = await app_client.get("/entities/")

    _assert_unauthorized(response)


@pytest.mark.parametrize(
    "authorization",
    [
        "Basic dXNlcjpwYXNz",
        "Bearer ",
        "Bearer not-a-jwt",
    ],
)
async def test_entity_routes_reject_malformed_authorization(
    app_client: httpx.AsyncClient,
    authorization: str,
) -> None:
    response = await app_client.get(
        "/entities/",
        headers={"Authorization": authorization},
    )

    _assert_unauthorized(response)


@pytest.mark.parametrize(
    "token_claims",
    [
        {"expires_in_seconds": -60},
        {"not_before_in_seconds": 300},
        {"audience": "wrong-client"},
        {"issuer": "https://wrong-idp/realm"},
        {"audience": "wrong-client", "roles": ("entities:write",)},
    ],
)
async def test_entity_routes_reject_invalid_token_claims(
    app_client: httpx.AsyncClient,
    token_factory: Callable[..., str],
    token_claims: dict[str, Any],
) -> None:
    response = await app_client.post(
        "/entities/",
        headers={"Authorization": f"Bearer {token_factory(**token_claims)}"},
        json={"name": "Never created"},
    )

    _assert_unauthorized(response)


@pytest.mark.parametrize(
    "forge",
    [
        pytest.param(
            lambda key, _foreign: make_hs256_token_signed_with_public_key(key),
            id="hs256-with-public-key",
        ),
        pytest.param(
            lambda _key, foreign: make_test_token(foreign),
            id="foreign-key-same-kid",
        ),
        pytest.param(lambda _key, _foreign: make_unsigned_token(), id="alg-none"),
        pytest.param(
            lambda key, _foreign: make_test_token(key, kid="rotated-away"),
            id="unknown-kid",
        ),
    ],
)
async def test_entity_routes_reject_cryptographically_invalid_tokens(
    app_client: httpx.AsyncClient,
    signing_private_key: RSAPrivateKey,
    foreign_private_key: RSAPrivateKey,
    forge: Callable[[RSAPrivateKey, RSAPrivateKey], str],
) -> None:
    token = forge(signing_private_key, foreign_private_key)

    response = await app_client.post(
        "/entities/",
        headers={"Authorization": f"Bearer {token}"},
        json={"name": "Never created"},
    )

    _assert_unauthorized(response)
    listing = await app_client.get(
        "/entities/",
        headers={"Authorization": f"Bearer {make_test_token(signing_private_key)}"},
    )
    assert listing.json() == []


@pytest.mark.parametrize(
    ("method", "path", "kwargs"),
    [
        ("post", "/entities/", {"json": {"name": "Reader"}}),
        ("put", f"/entities/{uuid4()}", {"json": {"name": "Reader"}}),
        ("delete", f"/entities/{uuid4()}", {}),
    ],
)
async def test_write_routes_require_the_entity_write_role(
    app_client: httpx.AsyncClient,
    token_factory: Callable[..., str],
    method: str,
    path: str,
    kwargs: dict[str, Any],
) -> None:
    headers = {"Authorization": f"Bearer {token_factory(roles=())}"}

    response = await app_client.request(method, path, headers=headers, **kwargs)

    body = _assert_problem_details(response, status_code=403, title="Forbidden")
    assert body["detail"] == "Role 'entities:write' is required"


async def test_read_routes_do_not_require_the_entity_write_role(
    app_client: httpx.AsyncClient,
    token_factory: Callable[..., str],
) -> None:
    headers = {"Authorization": f"Bearer {token_factory(roles=())}"}

    response = await app_client.get("/entities/", headers=headers)

    assert response.status_code == 200
    assert response.json() == []


@WithAuth
async def test_create_entity_persists_and_returns_aware_timestamps(
    app_client: httpx.AsyncClient,
) -> None:
    create_response = await app_client.post(
        "/entities/",
        json={"name": "Persisted entity", "description": "Persisted description"},
    )
    assert create_response.status_code == 201
    created = create_response.json()
    assert created["id"]
    assert created["name"] == "Persisted entity"
    assert created["description"] == "Persisted description"
    assert created["created_at"].endswith(("Z", "+00:00"))
    assert created["updated_at"].endswith(("Z", "+00:00"))

    get_response = await app_client.get(f"/entities/{created['id']}")
    assert get_response.status_code == 200
    assert get_response.json() == created


@WithAuth
@pytest.mark.parametrize(
    "payload",
    [
        pytest.param({"name": "x" * 255}, id="name-at-max-length"),
        pytest.param(
            {"name": "ok", "description": "d" * 5000}, id="description-at-max"
        ),
        pytest.param({"name": "Ünïcödé 名前 🚀", "description": "é"}, id="unicode"),
    ],
)
async def test_create_entity_accepts_boundary_and_unicode_payloads(
    app_client: httpx.AsyncClient,
    payload: dict[str, str],
) -> None:
    create_response = await app_client.post("/entities/", json=payload)

    assert create_response.status_code == 201
    created = create_response.json()
    assert created["name"] == payload["name"]
    assert created["description"] == payload.get("description")
    fetched = await app_client.get(f"/entities/{created['id']}")
    assert fetched.json()["name"] == payload["name"]


@WithAuth
async def test_list_entities_orders_and_paginates(
    app_client: httpx.AsyncClient,
) -> None:
    for name in ("Beta", "Alpha", "Gamma"):
        response = await app_client.post("/entities/", json={"name": name})
        assert response.status_code == 201

    descending = await app_client.get("/entities/?order_by=name&order_direction=desc")
    middle = await app_client.get("/entities/?order_by=name&offset=1&limit=1")
    beyond = await app_client.get("/entities/?offset=3")

    assert [entity["name"] for entity in descending.json()] == [
        "Gamma",
        "Beta",
        "Alpha",
    ]
    assert [entity["name"] for entity in middle.json()] == ["Beta"]
    assert beyond.json() == []


@WithAuth
async def test_update_entity_replaces_the_whole_resource(
    app_client: httpx.AsyncClient,
) -> None:
    created_response = await app_client.post(
        "/entities/",
        json={"name": "Before update", "description": "Description before update"},
    )
    assert created_response.status_code == 201
    entity_id = created_response.json()["id"]

    update_response = await app_client.put(
        f"/entities/{entity_id}",
        json={"name": "After update"},
    )

    assert update_response.status_code == 200
    updated = update_response.json()
    assert updated["id"] == entity_id
    assert updated["name"] == "After update"
    assert updated["description"] is None

    get_response = await app_client.get(f"/entities/{entity_id}")
    assert get_response.status_code == 200
    assert get_response.json()["description"] is None


@WithAuth
async def test_delete_entity_removes_the_persisted_record(
    app_client: httpx.AsyncClient,
) -> None:
    created_response = await app_client.post(
        "/entities/",
        json={"name": "Delete me"},
    )
    assert created_response.status_code == 201
    entity_id = created_response.json()["id"]

    delete_response = await app_client.delete(f"/entities/{entity_id}")
    assert delete_response.status_code == 204
    assert not delete_response.content

    get_response = await app_client.get(f"/entities/{entity_id}")
    body = _assert_problem_details(get_response, status_code=404, title="Not Found")
    assert body["detail"] == f"Entity '{entity_id}' not found"


@WithAuth
@pytest.mark.parametrize(
    ("method", "path_template", "kwargs"),
    [
        ("get", "/entities/{entity_id}", {}),
        ("put", "/entities/{entity_id}", {"json": {"name": "Missing entity"}}),
        ("delete", "/entities/{entity_id}", {}),
    ],
)
async def test_missing_entity_operations_return_not_found(
    app_client: httpx.AsyncClient,
    method: str,
    path_template: str,
    kwargs: dict[str, Any],
) -> None:
    entity_id = uuid4()

    response = await app_client.request(
        method, path_template.format(entity_id=entity_id), **kwargs
    )

    body = _assert_problem_details(response, status_code=404, title="Not Found")
    assert body["detail"] == f"Entity '{entity_id}' not found"


@WithAuth
@pytest.mark.parametrize(
    ("payload", "expected_location"),
    [
        ({}, ("body", "name")),
        ({"description": "Missing name"}, ("body", "name")),
        ({"name": "", "description": "Invalid"}, ("body", "name")),
        ({"name": "x" * 256}, ("body", "name")),
        ({"name": "Valid name", "description": "x" * 5001}, ("body", "description")),
        ({"name": "Valid name", "unknown_field": "typo"}, ("body", "unknown_field")),
    ],
)
async def test_create_entity_rejects_invalid_payloads(
    app_client: httpx.AsyncClient,
    payload: dict[str, Any],
    expected_location: tuple[str, ...],
) -> None:
    response = await app_client.post("/entities/", json=payload)

    _assert_validation_problem(response, expected_location=expected_location)


@WithAuth
async def test_create_entity_rejects_missing_body(
    app_client: httpx.AsyncClient,
) -> None:
    response = await app_client.post("/entities/")

    _assert_validation_problem(response, expected_location=("body",))


@WithAuth
@pytest.mark.parametrize(
    ("query_string", "expected_location"),
    [
        ("offset=-1", ("query", "offset")),
        ("limit=0", ("query", "limit")),
        ("limit=101", ("query", "limit")),
        ("order_by=id", ("query", "order_by")),
        ("order_direction=sideways", ("query", "order_direction")),
    ],
)
async def test_list_entities_rejects_invalid_pagination(
    app_client: httpx.AsyncClient,
    query_string: str,
    expected_location: tuple[str, ...],
) -> None:
    response = await app_client.get(f"/entities/?{query_string}")

    _assert_validation_problem(response, expected_location=expected_location)


@WithAuth
async def test_get_entity_rejects_invalid_uuid(
    app_client: httpx.AsyncClient,
) -> None:
    response = await app_client.get("/entities/not-a-uuid")

    _assert_validation_problem(response, expected_location=("path", "entity_id"))


@WithAuth
@pytest.mark.parametrize(
    ("payload", "expected_location"),
    [
        ({}, ("body", "name")),
        ({"name": ""}, ("body", "name")),
        ({"name": "x" * 256}, ("body", "name")),
        ({"name": "Valid update", "description": "x" * 5001}, ("body", "description")),
        ({"name": "Valid update", "extra": True}, ("body", "extra")),
    ],
)
async def test_update_entity_rejects_invalid_payloads(
    app_client: httpx.AsyncClient,
    payload: dict[str, Any],
    expected_location: tuple[str, ...],
) -> None:
    response = await app_client.put(f"/entities/{uuid4()}", json=payload)

    _assert_validation_problem(response, expected_location=expected_location)
