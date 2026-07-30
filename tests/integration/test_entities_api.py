from collections.abc import Callable
from typing import Any
from uuid import uuid4

import httpx
import pytest

from app.auth import Permission
from app.exceptions import AuthorizationError
from tests.integration.conftest import WithAuth

pytestmark = pytest.mark.integration


def _assert_problem_details(
    response: httpx.Response,
    *,
    status_code: int,
    title: str,
) -> dict[str, Any]:
    assert response.status_code == status_code
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
        status_code=400,
        title="Bad Request",
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


@WithAuth
async def test_entity_route_returns_forbidden_when_permission_is_denied(
    app_client: httpx.AsyncClient,
    permission_authorizer: Any,
) -> None:
    permission_authorizer.authorize.side_effect = AuthorizationError()

    response = await app_client.get("/entities/")

    problem = _assert_problem_details(
        response,
        status_code=403,
        title="Forbidden",
    )
    assert problem["detail"] == "Forbidden"


@WithAuth
@pytest.mark.parametrize(
    "request_case",
    [
        (
            "post",
            "/entities/",
            {"json": {"name": "Permission check"}},
            Permission.ENTITY_CREATE,
        ),
        ("get", "/entities/", {}, Permission.ENTITY_LIST),
        (
            "get",
            f"/entities/{uuid4()}",
            {},
            Permission.ENTITY_READ,
        ),
        (
            "put",
            f"/entities/{uuid4()}",
            {"json": {"name": "Permission check"}},
            Permission.ENTITY_UPDATE,
        ),
        (
            "delete",
            f"/entities/{uuid4()}",
            {},
            Permission.ENTITY_DELETE,
        ),
    ],
)
async def test_each_entity_route_requires_its_declared_permission(
    app_client: httpx.AsyncClient,
    permission_authorizer: Any,
    request_case: tuple[str, str, dict[str, Any], Permission],
) -> None:
    method, path, kwargs, permission = request_case
    await app_client.request(method, path, **kwargs)

    permission_authorizer.authorize.assert_awaited_once()
    assert permission_authorizer.authorize.await_args.args[1] == (permission,)


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
        {"audience": "wrong-client"},
        {"issuer": "https://wrong-idp/realm"},
    ],
)
async def test_entity_routes_reject_invalid_token_claims(
    app_client: httpx.AsyncClient,
    make_test_token: Callable[..., str],
    token_claims: dict[str, Any],
) -> None:
    response = await app_client.get(
        "/entities/",
        headers={"Authorization": f"Bearer {make_test_token(**token_claims)}"},
    )

    _assert_unauthorized(response)


@WithAuth
async def test_entities_crud_flow(app_client: httpx.AsyncClient) -> None:
    create_response = await app_client.post(
        "/entities/",
        json={"name": "Created entity", "description": "Created description"},
    )
    assert create_response.status_code == 201
    created = create_response.json()
    entity_id = created["id"]
    assert created["name"] == "Created entity"
    assert created["description"] == "Created description"

    get_response = await app_client.get(f"/entities/{entity_id}")
    assert get_response.status_code == 200
    assert get_response.json()["id"] == entity_id

    list_response = await app_client.get("/entities/")
    assert list_response.status_code == 200
    assert any(entity["id"] == entity_id for entity in list_response.json())

    update_response = await app_client.put(
        f"/entities/{entity_id}",
        json={"name": "Updated entity"},
    )
    assert update_response.status_code == 200
    updated = update_response.json()
    assert updated["id"] == entity_id
    assert updated["name"] == "Updated entity"
    assert updated["description"] == "Created description"

    delete_response = await app_client.delete(f"/entities/{entity_id}")
    assert delete_response.status_code == 204
    assert not delete_response.content

    missing_response = await app_client.get(f"/entities/{entity_id}")
    assert missing_response.status_code == 404
    assert missing_response.json()["title"] == "Not Found"


@WithAuth
async def test_create_entity_persists_and_returns_response(
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
    assert created["created_at"]
    assert created["updated_at"]

    get_response = await app_client.get(f"/entities/{created['id']}")
    assert get_response.status_code == 200
    assert get_response.json() == created


@WithAuth
async def test_list_entities_returns_persisted_entities(
    app_client: httpx.AsyncClient,
) -> None:
    first = await app_client.post("/entities/", json={"name": "First entity"})
    second = await app_client.post(
        "/entities/",
        json={"name": "Second entity", "description": "Second description"},
    )
    assert first.status_code == 201
    assert second.status_code == 201

    response = await app_client.get("/entities/")

    assert response.status_code == 200
    listed_ids = {entity["id"] for entity in response.json()}
    assert {first.json()["id"], second.json()["id"]} <= listed_ids


@WithAuth
async def test_update_entity_persists_changes_and_can_clear_description(
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
        json={"name": "After update", "description": None},
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
    request = getattr(app_client, method)

    response = await request(path_template.format(entity_id=entity_id), **kwargs)

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
async def test_list_entities_orders_by_one_selected_column(
    app_client: httpx.AsyncClient,
) -> None:
    for name in ("Beta", "Alpha", "Gamma"):
        response = await app_client.post("/entities/", json={"name": name})
        assert response.status_code == 201

    response = await app_client.get("/entities/?order_by=name&order_direction=desc")

    assert response.status_code == 200
    assert [entity["name"] for entity in response.json()] == [
        "Gamma",
        "Beta",
        "Alpha",
    ]


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
    ],
)
async def test_update_entity_rejects_invalid_payloads(
    app_client: httpx.AsyncClient,
    payload: dict[str, Any],
    expected_location: tuple[str, ...],
) -> None:
    response = await app_client.put(f"/entities/{uuid4()}", json=payload)

    _assert_validation_problem(response, expected_location=expected_location)
