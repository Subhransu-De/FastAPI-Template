from datetime import UTC, datetime
from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.io.entity import EntityCreate, EntityOrderBy, EntityResponse, EntityUpdate
from app.model.entity import Entity

pytestmark = pytest.mark.unit


def test_entity_order_fields_match_every_table_column_except_id() -> None:
    table_columns = {column.name for column in Entity.__table__.columns} - {"id"}

    assert {field.value for field in EntityOrderBy} == table_columns


@pytest.mark.parametrize("schema", [EntityCreate, EntityUpdate])
def test_request_schemas_reject_unknown_fields(
    schema: type[EntityCreate] | type[EntityUpdate],
) -> None:
    with pytest.raises(ValidationError, match="extra_forbidden"):
        schema.model_validate({"name": "Valid", "unknown_field": "typo"})


def test_entity_response_rejects_naive_timestamps() -> None:
    naive = datetime(2026, 1, 1, 12, 0, 0)  # noqa: DTZ001

    with pytest.raises(ValidationError):
        EntityResponse(
            id=uuid4(),
            name="Naive",
            description=None,
            created_at=naive,
            updated_at=naive,
        )


def test_entity_response_validates_from_a_persisted_entity() -> None:
    entity = Entity(
        id=uuid4(),
        name="Persisted entity",
        description=None,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )

    response = EntityResponse.model_validate(entity)

    assert response.model_dump() == {
        "id": entity.id,
        "name": "Persisted entity",
        "description": None,
        "created_at": entity.created_at,
        "updated_at": entity.updated_at,
    }
