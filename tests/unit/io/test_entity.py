from datetime import UTC, datetime
from types import SimpleNamespace
from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.io.entity import EntityCreate, EntityResponse, EntityUpdate

pytestmark = pytest.mark.unit


def test_entity_create_accepts_valid_payload() -> None:
    payload = EntityCreate(name="Test entity", description="Description")

    assert payload.name == "Test entity"
    assert payload.description == "Description"


def test_entity_create_rejects_empty_name() -> None:
    with pytest.raises(ValidationError):
        EntityCreate(name="", description=None)


def test_entity_update_requires_name() -> None:
    with pytest.raises(ValidationError):
        EntityUpdate(description="Updated description")


def test_entity_update_rejects_empty_name() -> None:
    with pytest.raises(ValidationError):
        EntityUpdate(name="")


def test_entity_update_rejects_null_name() -> None:
    with pytest.raises(ValidationError):
        EntityUpdate.model_validate({"name": None})


def test_entity_response_validates_from_entity_like_object() -> None:
    entity_id = uuid4()
    created_at = datetime.now(UTC)
    updated_at = datetime.now(UTC)
    entity = SimpleNamespace(
        id=entity_id,
        name="Persisted entity",
        description="Persisted description",
        created_at=created_at,
        updated_at=updated_at,
    )

    response = EntityResponse.model_validate(entity)

    assert response.id == entity_id
    assert response.name == "Persisted entity"
    assert response.description == "Persisted description"
    assert response.created_at == created_at
    assert response.updated_at == updated_at
