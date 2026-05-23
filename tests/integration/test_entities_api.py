import httpx
import pytest

pytestmark = pytest.mark.integration


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


async def test_create_entity_with_empty_name_returns_validation_error(
    app_client: httpx.AsyncClient,
) -> None:
    response = await app_client.post(
        "/entities/",
        json={"name": "", "description": "Invalid"},
    )

    assert response.status_code == 400
    assert response.json()["title"] == "Bad Request"


async def test_list_entities_rejects_limit_above_100(
    app_client: httpx.AsyncClient,
) -> None:
    response = await app_client.get("/entities/?limit=101")

    assert response.status_code == 400
    assert response.json()["title"] == "Bad Request"
