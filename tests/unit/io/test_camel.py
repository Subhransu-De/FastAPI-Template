from dataclasses import dataclass
from typing import Annotated
from uuid import UUID, uuid4

import httpx
import pytest
from fastapi import APIRouter, FastAPI, Path
from pydantic import ValidationError

from app.io import CamelModel, CamelResponse

pytestmark = pytest.mark.unit


class UserUpdate(CamelModel):
    first_name: str


class UserResponse(CamelResponse):
    user_id: UUID
    first_name: str


@dataclass
class User:
    user_id: UUID
    first_name: str


route = APIRouter(prefix="/users")


@route.put("/{userId}", response_model=UserResponse)
async def update_user(
    user_id: Annotated[UUID, Path(alias="userId")],
    data: UserUpdate,
) -> User:
    return User(user_id=user_id, first_name=data.first_name)


@pytest.fixture
def app() -> FastAPI:
    app = FastAPI()
    app.include_router(route)
    return app


def _client(app: FastAPI) -> httpx.AsyncClient:
    return httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="https://testserver"
    )


def test_camel_model_reads_and_dumps_camel_case_keys() -> None:
    update = UserUpdate.model_validate({"firstName": "Ada"})

    assert update.first_name == "Ada"
    assert update.model_dump() == {"firstName": "Ada"}


def test_camel_model_rejects_snake_case_keys() -> None:
    with pytest.raises(ValidationError) as error:
        UserUpdate.model_validate({"first_name": "Ada"})

    assert {(e["type"], e["loc"]) for e in error.value.errors()} == {
        ("missing", ("firstName",)),
        ("extra_forbidden", ("first_name",)),
    }


def test_camel_response_reads_snake_case_attributes() -> None:
    user = User(user_id=uuid4(), first_name="Ada")

    response = UserResponse.model_validate(user)

    assert response.model_dump() == {"userId": user.user_id, "firstName": "Ada"}


async def test_camel_path_parameter_and_body_round_trip(app: FastAPI) -> None:
    user_id = uuid4()

    async with _client(app) as client:
        response = await client.put(f"/users/{user_id}", json={"firstName": "Ada"})

    assert response.status_code == 200
    assert response.json() == {"userId": str(user_id), "firstName": "Ada"}


async def test_camel_route_rejects_a_snake_case_body(app: FastAPI) -> None:
    async with _client(app) as client:
        response = await client.put(f"/users/{uuid4()}", json={"first_name": "Ada"})

    assert response.status_code == 422
    assert {(e["type"], tuple(e["loc"])) for e in response.json()["detail"]} == {
        ("missing", ("body", "firstName")),
        ("extra_forbidden", ("body", "first_name")),
    }


def test_camel_path_parameter_is_named_by_its_alias_in_openapi(app: FastAPI) -> None:
    operation = app.openapi()["paths"]["/users/{userId}"]["put"]

    assert [(p["name"], p["in"]) for p in operation["parameters"]] == [
        ("userId", "path")
    ]
