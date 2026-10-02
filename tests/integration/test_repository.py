from collections.abc import AsyncGenerator
from uuid import UUID, uuid4

import pytest
from sqlalchemy import String
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from app.database import SessionMaker
from app.model import Entity, IntegerPrimaryKey
from app.repository import Ordering, Repository

pytestmark = pytest.mark.integration


@pytest.fixture
async def session(
    integration_sessionmaker: SessionMaker,
    clean_integration_database: None,
) -> AsyncGenerator[AsyncSession]:
    async with integration_sessionmaker() as session:
        yield session
        await session.rollback()


@pytest.fixture
def repository(session: AsyncSession) -> Repository[Entity, UUID]:
    return Repository(Entity, session)


@pytest.fixture
async def three_entities(repository: Repository[Entity, UUID]) -> list[Entity]:
    entities = [
        Entity(name="Alpha", description="First"),
        Entity(name="Beta", description=None),
        Entity(name="Gamma", description="Third"),
    ]
    await repository.save_all(entities)
    return entities


async def test_save_all_assigns_ids_and_aware_timestamps(
    repository: Repository[Entity, UUID],
) -> None:
    entities = [Entity(name="Alpha", description=None), Entity(name="Beta")]

    saved = await repository.save_all(entities)

    assert list(saved) == entities
    for entity in entities:
        assert entity.id is not None
        assert entity.created_at.tzinfo is not None
        assert entity.updated_at.utcoffset() is not None
        offset = entity.updated_at.utcoffset()
        assert offset is not None
        assert offset.total_seconds() == 0


async def test_lookups_by_id(
    repository: Repository[Entity, UUID],
    three_entities: list[Entity],
) -> None:
    alpha, beta, gamma = three_entities

    assert await repository.find_by_id(beta.id) is beta
    assert await repository.find_by_id(uuid4()) is None
    assert await repository.exists_by_id(alpha.id) is True
    assert await repository.exists_by_id(uuid4()) is False
    selected = await repository.find_all_by_id([gamma.id, alpha.id, uuid4()])
    assert {entity.id for entity in selected} == {alpha.id, gamma.id}


async def test_find_by_applies_every_predicate(
    repository: Repository[Entity, UUID],
    three_entities: list[Entity],
) -> None:
    _, beta, gamma = three_entities

    named_beta = await repository.find_by(Entity.name == "Beta")
    described_not_alpha = await repository.find_by(
        Entity.description.is_not(None), Entity.name != "Alpha"
    )
    everything = await repository.find_by()

    assert [entity.id for entity in named_beta] == [beta.id]
    assert [entity.id for entity in described_not_alpha] == [gamma.id]
    assert len(everything) == 3


async def test_pagination_applies_offset_limit_and_ordering(
    repository: Repository[Entity, UUID],
    three_entities: list[Entity],
) -> None:
    ascending = await repository.find_all_paginated(
        offset=1, limit=1, ordering=Ordering(column=Entity.name)
    )
    descending = await repository.find_all_paginated(
        limit=2, ordering=Ordering(column=Entity.name, descending=True)
    )
    beyond = await repository.find_all_paginated(offset=10)

    assert [entity.name for entity in ascending] == ["Beta"]
    assert [entity.name for entity in descending] == ["Gamma", "Beta"]
    assert list(beyond) == []


async def test_empty_id_collections_short_circuit(
    repository: Repository[Entity, UUID],
) -> None:
    assert await repository.find_all_by_id([]) == []
    assert await repository.delete_all_by_id([]) == 0


async def test_update_merges_and_refreshes_entity(
    repository: Repository[Entity, UUID],
) -> None:
    entity = await repository.save(Entity(name="Original", description="Before"))
    entity.name = "Updated"
    entity.description = None

    updated = await repository.update(entity)

    assert updated.id == entity.id
    assert updated.name == "Updated"
    assert updated.description is None
    found = await repository.find_by_id(entity.id)
    assert found is updated


async def test_deletes_return_real_database_row_counts(
    repository: Repository[Entity, UUID],
) -> None:
    first = await repository.save(Entity(name="Delete one", description=None))
    second = await repository.save(Entity(name="Delete many", description=None))

    assert await repository.delete_by_id(first.id) is True
    assert await repository.find_by_id(first.id) is None
    assert await repository.delete_by_id(first.id) is False
    assert await repository.delete_all_by_id([second.id, uuid4()]) == 1
    assert await repository.find_by_id(second.id) is None


class _IntegerKeyBase(DeclarativeBase):
    pass


class Counter(IntegerPrimaryKey, _IntegerKeyBase):
    __tablename__ = "integer_key_counters"

    label: Mapped[str] = mapped_column(String(50))


@pytest.fixture
async def counter_repository(
    integration_engine: AsyncEngine,
    session: AsyncSession,
) -> AsyncGenerator[Repository[Counter, int]]:
    async with integration_engine.begin() as connection:
        await connection.run_sync(_IntegerKeyBase.metadata.create_all)
    try:
        yield Repository(Counter, session)
    finally:
        await session.rollback()
        async with integration_engine.begin() as connection:
            await connection.run_sync(_IntegerKeyBase.metadata.drop_all)


async def test_integer_keyed_model_round_trips_through_repository(
    counter_repository: Repository[Counter, int],
) -> None:
    first, second = await counter_repository.save_all(
        [Counter(label="first"), Counter(label="second")]
    )

    assert isinstance(first.id, int)
    assert second.id > first.id
    assert await counter_repository.find_by_id(first.id) is first
    assert await counter_repository.exists_by_id(second.id + 1) is False

    first.label = "renamed"
    updated = await counter_repository.update(first)
    assert updated.label == "renamed"

    assert await counter_repository.delete_by_id(first.id) is True
    assert await counter_repository.find_by_id(first.id) is None
    assert await counter_repository.delete_all_by_id([second.id, second.id + 1]) == 1
    assert list(await counter_repository.find_all()) == []
