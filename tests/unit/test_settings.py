import os

import pytest
from pydantic import ValidationError

from app.settings.config import Settings


pytestmark = pytest.mark.unit


class TestSettings:
    def test_settings_requires_database_url(self, monkeypatch):
        monkeypatch.delenv("DATABASE_URL", raising=False)
        monkeypatch.setattr("app.settings.config.Settings.model_config", {"env_file": None})

        with pytest.raises(ValidationError) as exc_info:
            Settings(_env_file=None)

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("database_url",) for e in errors)

    def test_settings_defaults(self, monkeypatch):
        monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg://user:pass@localhost/db")

        settings = Settings(_env_file=None)

        assert settings.app_name == "FastAPI Template"
        assert settings.port == 80
        assert settings.database_pool_size == 5
        assert settings.database_max_overflow == 10
        assert settings.database_echo is False
        assert settings.database_pool_pre_ping is True
