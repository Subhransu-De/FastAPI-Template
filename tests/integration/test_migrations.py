import pytest
from alembic.config import Config

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
