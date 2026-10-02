import pytest
from alembic.config import Config
from alembic.script import ScriptDirectory

pytestmark = pytest.mark.unit


def test_migration_history_is_linear() -> None:
    config = Config("alembic.ini")
    config.set_main_option("script_location", "alembic")

    script = ScriptDirectory.from_config(config)

    assert len(script.get_heads()) == 1
    revisions = list(script.walk_revisions())
    assert all(revision.down_revision is not None for revision in revisions[:-1])
