import pytest

from app.settings.config import Settings

pytestmark = pytest.mark.unit


@pytest.fixture(autouse=True)
def _mock_get_session(monkeypatch):
    async def _dummy_get_session():
        yield None

    monkeypatch.setattr("app.database.get_session", _dummy_get_session)


class TestSettings:
    def test_settings_uses_dummy_database_url_when_missing(self, monkeypatch):
        monkeypatch.delenv("DATABASE_URL", raising=False)
        monkeypatch.setattr(
            "app.settings.config.Settings.model_config", {"env_file": None}
        )

        settings = Settings(_env_file=None)  # ty: ignore[unknown-argument]

        assert settings.database_url == "dummy://"

    def test_settings_defaults(self, monkeypatch):
        monkeypatch.setenv(
            "DATABASE_URL", "postgresql+psycopg://user:pass@localhost/db"
        )

        settings = Settings(_env_file=None)  # ty: ignore[unknown-argument]

        assert settings.app_name == "FastAPI Template"
        assert settings.port == 80
        assert settings.database_pool_size == 5
        assert settings.database_max_overflow == 10
        assert settings.database_echo is False
        assert settings.database_pool_pre_ping is True
