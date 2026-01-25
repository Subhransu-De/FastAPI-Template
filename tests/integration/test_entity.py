from uuid import UUID, uuid4

import pytest

pytestmark = pytest.mark.integration


def assert_entity_response(entity, name, description):
    UUID(entity["id"])
    assert entity["name"] == name
    assert entity["description"] == description
    assert "created_at" in entity
    assert "updated_at" in entity


async def create_entity(client, name="Entity A", description="Desc A"):
    response = await client.post(
        "/entities/",
        json={"name": name, "description": description},
    )
    assert response.status_code == 201
    return response.json()


async def test_create_and_get_entity(client):
    created = await create_entity(client)

    response = await client.get(f"/entities/{created['id']}")

    assert response.status_code == 200
    assert_entity_response(response.json(), "Entity A", "Desc A")


async def test_list_entities_with_pagination(client):
    first = await create_entity(client, name="Entity A", description="Desc A")
    second = await create_entity(client, name="Entity B", description="Desc B")

    response = await client.get("/entities/?offset=0&limit=1")

    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["id"] in {first["id"], second["id"]}

    response = await client.get("/entities/?offset=1&limit=1")

    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1


async def test_update_entity(client):
    created = await create_entity(client)

    response = await client.put(
        f"/entities/{created['id']}",
        json={"name": "Entity Updated", "description": "Desc Updated"},
    )

    assert response.status_code == 200
    assert_entity_response(response.json(), "Entity Updated", "Desc Updated")


async def test_delete_entity(client):
    created = await create_entity(client)

    response = await client.delete(f"/entities/{created['id']}")

    assert response.status_code == 204

    response = await client.get(f"/entities/{created['id']}")

    assert response.status_code == 404
    body = response.json()
    assert body["title"] == "Not Found"
    assert body["status"] == 404
    assert body["detail"] == f"Entity '{created['id']}' not found"


async def test_create_entity_validation_error(client):
    response = await client.post("/entities/", json={"description": "Missing name"})

    assert response.status_code == 400
    body = response.json()
    assert body["title"] == "Bad Request"
    assert body["status"] == 400
    assert isinstance(body["detail"], list)


async def test_get_entity_not_found(client):
    missing_id = uuid4()

    response = await client.get(f"/entities/{missing_id}")

    assert response.status_code == 404
    body = response.json()
    assert body["title"] == "Not Found"
    assert body["status"] == 404
    assert body["detail"] == f"Entity '{missing_id}' not found"
