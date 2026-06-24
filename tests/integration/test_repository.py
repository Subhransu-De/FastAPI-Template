from collections.abc import AsyncGenerator
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.model.entity import Entity
from app.repository.base import BaseRepository

pytestmark = pytest.mark.integration


@pytest.fixture
async def session(
    integration_sessionmaker: async_sessionmaker[AsyncSession],
    clean_integration_database: None,
) -> AsyncGenerator[AsyncSession]:
    async with integration_sessionmaker() as session:
        yield session
        await session.rollback()


@pytest.fixture
def repository(session: AsyncSession) -> BaseRepository[Entity]:
    return BaseRepository(Entity, session)


async def test_repository_persists_and_queries_entities_with_real_database(
    repository: BaseRepository[Entity],
) -> None:
    alpha = Entity(name="Alpha", description="First")
    beta = Entity(name="Beta", description=None)
    gamma = Entity(name="Gamma", description="Third")

    saved_entities = await repository.save_all([alpha, beta, gamma])

    assert saved_entities == [alpha, beta, gamma]
    assert all(entity.id for entity in saved_entities)
    assert all(entity.created_at for entity in saved_entities)
    assert all(entity.updated_at for entity in saved_entities)

    assert await repository.find_by_id(beta.id) is beta
    assert await repository.find_by_id(uuid4()) is None
    assert await repository.exists_by_id(alpha.id) is True
    assert await repository.exists_by_id(uuid4()) is False

    named_beta = await repository.find_by(name="Beta")
    assert [entity.id for entity in named_beta] == [beta.id]

    selected = await repository.find_all_by_id([gamma.id, alpha.id])
    assert {entity.id for entity in selected} == {alpha.id, gamma.id}

    all_entities = await repository.find_all()
    assert {entity.id for entity in all_entities} == {alpha.id, beta.id, gamma.id}

    page = await repository.find_all_paginated(
        offset=1,
        limit=1,
        order_by=Entity.name.asc(),
    )
    assert [entity.name for entity in page] == ["Beta"]

    assert await repository.find_all_by_id([]) == []


async def test_repository_update_merges_and_refreshes_entity(
    repository: BaseRepository[Entity],
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
    assert found.name == "Updated"
    assert found.description is None


async def test_repository_deletes_return_real_database_row_counts(
    repository: BaseRepository[Entity],
) -> None:
    first = await repository.save(Entity(name="Delete one", description=None))
    second = await repository.save(Entity(name="Delete many", description=None))

    assert await repository.delete_by_id(first.id) is True
    assert await repository.find_by_id(first.id) is None
    assert await repository.delete_by_id(first.id) is False

    deleted_count = await repository.delete_all_by_id([second.id, uuid4()])
    assert deleted_count == 1
    assert await repository.find_by_id(second.id) is None
    assert await repository.delete_all_by_id([]) == 0
