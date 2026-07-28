from datetime import UTC, datetime

import httpx
import pytest

from tests.integration.conftest import WithAuth

pytestmark = [pytest.mark.integration, WithAuth]

EXPECTED_OPERATIONS = {
    "addOwner",
    "addPetToOwner",
    "addPetType",
    "addSpecialty",
    "addUser",
    "addVet",
    "addVisit",
    "addVisitToOwner",
    "deleteOwner",
    "deletePet",
    "deletePetType",
    "deleteSpecialty",
    "deleteVet",
    "deleteVisit",
    "failingRequest",
    "getOwner",
    "getOwnersPet",
    "getPet",
    "getPetType",
    "getSpecialty",
    "getVet",
    "getVisit",
    "listOwners",
    "listOwnersPage",
    "listPets",
    "listPetsPage",
    "listPetTypes",
    "listSpecialties",
    "listVets",
    "listVisits",
    "updateOwner",
    "updateOwnersPet",
    "updatePet",
    "updatePetType",
    "updateSpecialty",
    "updateVet",
    "updateVisit",
}

OWNER = {
    "firstName": "Jane",
    "lastName": "Doe",
    "address": "10 Main Street",
    "city": "Madison",
    "telephone": "6085550100",
}


async def _create_owner(client: httpx.AsyncClient) -> dict:
    response = await client.post("/api/owners", json=OWNER)
    assert response.status_code == 201, response.text
    assert response.headers["location"].startswith("/api/owners/")
    return response.json()


async def _create_pet_type(client: httpx.AsyncClient, name: str = "capybara") -> dict:
    response = await client.post("/api/pettypes", json={"name": name})
    assert response.status_code == 201, response.text
    return response.json()


async def _create_pet(
    client: httpx.AsyncClient,
    owner_id: int,
    pet_type: dict,
    name: str = "Pepper",
) -> dict:
    response = await client.post(
        f"/api/owners/{owner_id}/pets",
        json={
            "name": name,
            "birthDate": "2020-01-02",
            "type": pet_type,
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


async def test_petclinic_routes_require_authentication(
    app_client: httpx.AsyncClient,
) -> None:
    response = await app_client.get(
        "/api/owners",
        headers={"Authorization": ""},
    )

    assert response.status_code == 401


async def test_openapi_exposes_the_complete_petclinic_contract(
    app_client: httpx.AsyncClient,
) -> None:
    document = (await app_client.get("/openapi.json")).json()
    operations = {
        operation["operationId"]
        for path, path_item in document["paths"].items()
        if path.startswith("/api")
        for method, operation in path_item.items()
        if method in {"get", "post", "put", "delete"}
    }

    assert operations == EXPECTED_OPERATIONS


async def test_owner_crud_search_and_pagination(
    app_client: httpx.AsyncClient,
) -> None:
    owner = await _create_owner(app_client)

    fetched = await app_client.get(f"/api/owners/{owner['id']}")
    assert fetched.status_code == 200
    assert fetched.json() == owner

    searched = await app_client.get("/api/owners", params={"lastName": "Do"})
    assert searched.status_code == 200
    assert [item["id"] for item in searched.json()] == [owner["id"]]

    page = await app_client.get("/api/v2/owners", params={"page": 0, "size": 1})
    assert page.status_code == 200
    assert page.json() == {
        "content": [owner],
        "page": 0,
        "size": 1,
        "totalElements": 1,
        "totalPages": 1,
    }

    updated = {**OWNER, "city": "Monona"}
    response = await app_client.put(f"/api/owners/{owner['id']}", json=updated)
    assert response.status_code == 204
    assert (await app_client.get(f"/api/owners/{owner['id']}")).json()["city"] == (
        "Monona"
    )

    response = await app_client.delete(f"/api/owners/{owner['id']}")
    assert response.status_code == 204
    assert (await app_client.get(f"/api/owners/{owner['id']}")).status_code == 404


async def test_empty_v1_lists_are_not_found_but_v2_pages_are_empty(
    app_client: httpx.AsyncClient,
) -> None:
    assert (await app_client.get("/api/owners")).status_code == 404
    assert (await app_client.get("/api/pets")).status_code == 404

    response = await app_client.get("/api/v2/pets")
    assert response.status_code == 200
    assert response.json()["content"] == []
    assert response.json()["totalElements"] == 0
    assert response.json()["totalPages"] == 0


async def test_owner_pet_and_visit_flow(app_client: httpx.AsyncClient) -> None:
    owner = await _create_owner(app_client)
    pet_type = await _create_pet_type(app_client)
    pet = await _create_pet(app_client, owner["id"], pet_type)

    assert pet["ownerId"] == owner["id"]
    assert pet["type"] == pet_type
    assert (
        await app_client.get(f"/api/owners/{owner['id']}/pets/{pet['id']}")
    ).status_code == 200
    assert (await app_client.get(f"/api/pets/{pet['id']}")).status_code == 200
    assert [item["id"] for item in (await app_client.get("/api/pets")).json()] == [
        pet["id"]
    ]
    assert (await app_client.get("/api/v2/pets", params={"size": 1})).json()[
        "totalElements"
    ] == 1

    pet_update = {
        "name": "Pepper II",
        "birthDate": "2020-01-02",
        "type": pet_type,
    }
    assert (
        await app_client.put(f"/api/pets/{pet['id']}", json=pet_update)
    ).status_code == 204
    assert (await app_client.get(f"/api/pets/{pet['id']}")).json()["name"] == (
        "Pepper II"
    )
    pet_update["name"] = "Pepper III"
    assert (
        await app_client.put(
            f"/api/owners/{owner['id']}/pets/{pet['id']}",
            json=pet_update,
        )
    ).status_code == 204

    nested_visit = await app_client.post(
        f"/api/owners/{owner['id']}/pets/{pet['id']}/visits",
        json={"description": "annual checkup"},
    )
    assert nested_visit.status_code == 201
    visit = nested_visit.json()
    assert visit["petId"] == pet["id"]
    assert visit["date"] == datetime.now(UTC).date().isoformat()

    updated_visit = await app_client.put(
        f"/api/visits/{visit['id']}",
        json={"date": "2025-04-01", "description": "follow-up"},
    )
    assert updated_visit.status_code == 204
    assert (await app_client.get(f"/api/visits/{visit['id']}")).json()[
        "description"
    ] == "follow-up"

    other_owner = await app_client.post(
        "/api/owners",
        json={**OWNER, "firstName": "John", "telephone": "6085550101"},
    )
    assert other_owner.status_code == 201
    assert (
        await app_client.get(f"/api/owners/{other_owner.json()['id']}/pets/{pet['id']}")
    ).status_code == 404

    assert (await app_client.delete(f"/api/pets/{pet['id']}")).status_code == 204
    assert (await app_client.get(f"/api/visits/{visit['id']}")).status_code == 404


async def test_reference_data_crud_and_conflicts(
    app_client: httpx.AsyncClient,
) -> None:
    pet_type = await _create_pet_type(app_client)
    assert (await app_client.get("/api/pettypes")).json() == [pet_type]

    duplicate = await app_client.post("/api/pettypes", json={"name": "CAPYBARA"})
    assert duplicate.status_code == 409

    response = await app_client.put(
        f"/api/pettypes/{pet_type['id']}",
        json={"name": "guinea pig"},
    )
    assert response.status_code == 204
    assert (await app_client.get(f"/api/pettypes/{pet_type['id']}")).json()[
        "name"
    ] == "guinea pig"

    specialty = await app_client.post(
        "/api/specialties",
        json={"name": "cardiology"},
    )
    assert specialty.status_code == 201
    specialty_id = specialty.json()["id"]
    assert (await app_client.get(f"/api/specialties/{specialty_id}")).status_code == 200
    assert (await app_client.get("/api/specialties")).status_code == 200
    assert (
        await app_client.put(
            f"/api/specialties/{specialty_id}",
            json={"name": "internal medicine"},
        )
    ).status_code == 204
    assert (
        await app_client.delete(f"/api/specialties/{specialty_id}")
    ).status_code == 204
    assert (
        await app_client.delete(f"/api/pettypes/{pet_type['id']}")
    ).status_code == 204


async def test_vet_crud_resolves_specialties_by_name(
    app_client: httpx.AsyncClient,
) -> None:
    specialty = (
        await app_client.post("/api/specialties", json={"name": "surgery"})
    ).json()
    vet_data = {
        "firstName": "Helen",
        "lastName": "Leary",
        "specialties": [specialty],
    }
    response = await app_client.post("/api/vets", json=vet_data)
    assert response.status_code == 201, response.text
    vet = response.json()
    assert vet["specialties"] == [specialty]
    assert (await app_client.get("/api/vets")).json() == [vet]

    update = {
        "firstName": "Helen",
        "lastName": "Carter",
        "specialties": [specialty],
    }
    assert (
        await app_client.put(f"/api/vets/{vet['id']}", json=update)
    ).status_code == 204
    assert (await app_client.get(f"/api/vets/{vet['id']}")).json()["lastName"] == (
        "Carter"
    )
    assert (await app_client.delete(f"/api/vets/{vet['id']}")).status_code == 204


async def test_global_visit_creation_and_deletion(
    app_client: httpx.AsyncClient,
) -> None:
    owner = await _create_owner(app_client)
    pet_type = await _create_pet_type(app_client)
    pet = await _create_pet(app_client, owner["id"], pet_type)

    response = await app_client.post(
        "/api/visits",
        json={
            "petId": pet["id"],
            "date": "2026-01-12",
            "description": "vaccination",
        },
    )
    assert response.status_code == 201
    visit = response.json()
    assert (await app_client.get("/api/visits")).json() == [visit]
    assert (await app_client.delete(f"/api/visits/{visit['id']}")).status_code == 204


async def test_user_creation_hashes_and_hides_password(
    app_client: httpx.AsyncClient,
) -> None:
    response = await app_client.post(
        "/api/users",
        json={
            "username": "operator",
            "password": "correct horse battery staple",
            "enabled": True,
            "roles": [{"name": "owner_admin"}],
        },
    )

    assert response.status_code == 201, response.text
    assert response.json()["username"] == "operator"
    assert response.json()["roles"][0]["name"] == "ROLE_OWNER_ADMIN"
    assert "password" not in response.json()
    assert (
        await app_client.post(
            "/api/users",
            json={
                "username": "operator",
                "password": "another secure password",
                "roles": [{"name": "admin"}],
            },
        )
    ).status_code == 409


@pytest.mark.parametrize(
    ("payload", "field"),
    [
        ({**OWNER, "telephone": "123"}, "telephone"),
        (
            {
                "name": "Future",
                "birthDate": "2999-01-01",
                "type": {"id": 1, "name": "cat"},
            },
            "birthDate",
        ),
    ],
)
async def test_petclinic_validation_returns_bad_request(
    app_client: httpx.AsyncClient,
    payload: dict,
    field: str,
) -> None:
    path = "/api/owners" if field == "telephone" else "/api/owners/1/pets"
    response = await app_client.post(path, json=payload)

    assert response.status_code == 400
    assert any(error["loc"][-1] == field for error in response.json()["detail"])
