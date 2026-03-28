from uuid import uuid4

import pytest

from app.model.entity import Entity
from app.repository.base import BaseRepository

pytestmark = pytest.mark.unit


class TestBaseRepository:
    @pytest.fixture
    def repository(self, async_session):
        return BaseRepository(Entity, async_session)

    async def test_save_and_find_by_id(self, repository, async_session):
        entity = Entity(name="Test Entity", description="Test description")

        saved = await repository.save(entity)
        await async_session.commit()

        found = await repository.find_by_id(saved.id)

        assert found is not None
        assert found.id == saved.id
        assert found.name == "Test Entity"

    async def test_find_by_id_not_found(self, repository):
        result = await repository.find_by_id(uuid4())
        assert result is None

    async def test_find_all_empty(self, repository):
        result = await repository.find_all()
        assert result == []

    async def test_find_all_paginated(self, repository, async_session):
        for i in range(5):
            await repository.save(Entity(name=f"Entity {i}", description=None))
        await async_session.commit()

        page1 = await repository.find_all_paginated(offset=0, limit=2)
        page2 = await repository.find_all_paginated(offset=2, limit=2)
        page3 = await repository.find_all_paginated(offset=4, limit=2)

        assert len(page1) == 2
        assert len(page2) == 2
        assert len(page3) == 1

    async def test_find_all_paginated_with_order_by(self, repository, async_session):
        await repository.save(Entity(name="Zulu", description=None))
        await repository.save(Entity(name="Alpha", description=None))
        await async_session.commit()

        result = await repository.find_all_paginated(
            offset=0,
            limit=10,
            order_by=Entity.name.asc(),
        )

        assert [entity.name for entity in result[:2]] == ["Alpha", "Zulu"]

    async def test_delete_by_id(self, repository, async_session):
        entity = Entity(name="To Delete", description=None)
        saved = await repository.save(entity)
        await async_session.commit()

        deleted = await repository.delete_by_id(saved.id)
        await async_session.commit()

        assert deleted is True
        assert await repository.find_by_id(saved.id) is None

    async def test_delete_by_id_not_found(self, repository):
        deleted = await repository.delete_by_id(uuid4())
        assert deleted is False

    async def test_exists_by_id(self, repository, async_session):
        entity = Entity(name="Exists", description=None)
        saved = await repository.save(entity)
        await async_session.commit()

        assert await repository.exists_by_id(saved.id) is True
        assert await repository.exists_by_id(uuid4()) is False

    async def test_update(self, repository, async_session):
        entity = Entity(name="Original", description=None)
        saved = await repository.save(entity)
        await async_session.commit()

        saved.name = "Updated"
        await repository.update(saved)
        await async_session.commit()

        found = await repository.find_by_id(saved.id)
        assert found.name == "Updated"

    async def test_find_by(self, repository, async_session):
        entity1 = Entity(name="Alpha", description="First")
        entity2 = Entity(name="Beta", description="Second")
        await repository.save(entity1)
        await repository.save(entity2)
        await async_session.commit()

        result = await repository.find_by(name="Alpha")

        assert len(result) == 1
        assert result[0].name == "Alpha"

    async def test_save_all(self, repository, async_session):
        entities = [
            Entity(name="Batch 1", description=None),
            Entity(name="Batch 2", description=None),
        ]

        saved = await repository.save_all(entities)
        await async_session.commit()

        assert len(saved) == 2
        assert all(e.id is not None for e in saved)

    async def test_find_all_by_id(self, repository, async_session):
        e1 = Entity(name="E1", description=None)
        e2 = Entity(name="E2", description=None)
        e3 = Entity(name="E3", description=None)
        await repository.save_all([e1, e2, e3])
        await async_session.commit()

        result = await repository.find_all_by_id([e1.id, e3.id])

        assert len(result) == 2
        names = {e.name for e in result}
        assert names == {"E1", "E3"}

    async def test_find_all_by_id_empty_list(self, repository):
        result = await repository.find_all_by_id([])
        assert result == []

    async def test_delete_all_by_id(self, repository, async_session):
        e1 = Entity(name="D1", description=None)
        e2 = Entity(name="D2", description=None)
        e3 = Entity(name="D3", description=None)
        await repository.save_all([e1, e2, e3])
        await async_session.commit()

        count = await repository.delete_all_by_id([e1.id, e2.id])
        await async_session.commit()

        assert count == 2
        assert await repository.find_by_id(e1.id) is None
        assert await repository.find_by_id(e2.id) is None
        assert await repository.find_by_id(e3.id) is not None

    async def test_delete_all_by_id_empty_list(self, repository):
        count = await repository.delete_all_by_id([])
        assert count == 0
