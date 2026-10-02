from typing import Annotated

import httpx
import pytest
from asgi_lifespan import LifespanManager
from cryptography.hazmat.primitives.asymmetric.rsa import RSAPrivateKey
from fastapi import Depends
from sqlalchemy import func, select

from app.database import SessionMaker
from app.io.entity import EntityCreate
from app.main import create_app
from app.model.entity import Entity
from app.service import EntityService, get_entity_service
from app.settings import Settings
from tests.integration.conftest import make_test_token

pytestmark = pytest.mark.integration


async def _count_entities(sessionmaker: SessionMaker) -> int:
    async with sessionmaker() as session:
        return (await session.execute(select(func.count(Entity.id)))).scalar_one()


async def test_a_failure_after_a_write_rolls_the_request_back(
    integration_settings: Settings,
    integration_sessionmaker: SessionMaker,
    clean_integration_database: None,
    signing_private_key: RSAPrivateKey,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "app.exceptions.handlers.logfire.exception",
        lambda *_args, **_kwargs: None,
    )
    app = create_app(integration_settings)

    @app.post("/probe/write-then-fail")
    async def write_then_fail(
        service: Annotated[EntityService, Depends(get_entity_service)],
    ) -> None:
        await service.create(EntityCreate(name="Should not survive"))
        message = "failure after write"
        raise RuntimeError(message)

    @app.post("/probe/write")
    async def write(
        service: Annotated[EntityService, Depends(get_entity_service)],
    ) -> None:
        await service.create(EntityCreate(name="Should survive"))

    async with LifespanManager(app) as manager:
        transport = httpx.ASGITransport(app=manager.app, raise_app_exceptions=False)
        async with httpx.AsyncClient(
            transport=transport,
            base_url="https://testserver",
            headers={"Authorization": f"Bearer {make_test_token(signing_private_key)}"},
        ) as client:
            failed = await client.post("/probe/write-then-fail")
            assert failed.status_code == 500
            assert await _count_entities(integration_sessionmaker) == 0

            succeeded = await client.post("/probe/write")
            assert succeeded.status_code == 200
            assert await _count_entities(integration_sessionmaker) == 1
