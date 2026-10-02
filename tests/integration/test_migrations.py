from datetime import UTC, datetime
from uuid import uuid4

import pytest
from alembic.config import Config
from sqlalchemy import create_engine, text

from alembic import command

pytestmark = pytest.mark.integration


def test_models_and_migrations_agree(
    alembic_config: Config,
    test_postgres_url: str,
) -> None:
    command.check(alembic_config)


def test_migrations_downgrade_and_upgrade_cleanly(
    alembic_config: Config,
    test_postgres_url: str,
) -> None:
    command.downgrade(alembic_config, "base")
    command.upgrade(alembic_config, "head")

    command.check(alembic_config)


def test_timestamp_migration_keeps_existing_instants_in_any_session_zone(
    alembic_config: Config,
    test_postgres_url: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    command.downgrade(alembic_config, "97f7686bdccd")
    sync_url = test_postgres_url
    engine = create_engine(sync_url)
    entity_id = uuid4()
    try:
        with engine.begin() as connection:
            connection.execute(
                text(
                    "INSERT INTO entities (id, name, created_at, updated_at) "
                    "VALUES (:id, 'legacy', '2026-01-01 12:00:00', '2026-01-01 12:00:00')"
                ),
                {"id": entity_id},
            )

        monkeypatch.setenv("PGTZ", "Asia/Kolkata")
        command.upgrade(alembic_config, "head")
        monkeypatch.delenv("PGTZ")

        with engine.connect() as connection:
            created_at = connection.execute(
                text("SELECT created_at FROM entities WHERE id = :id"),
                {"id": entity_id},
            ).scalar_one()
    finally:
        with engine.begin() as connection:
            connection.execute(
                text("DELETE FROM entities WHERE id = :id"), {"id": entity_id}
            )
        engine.dispose()

    assert created_at == datetime(2026, 1, 1, 12, 0, tzinfo=UTC)
