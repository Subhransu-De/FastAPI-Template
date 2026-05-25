import pytest
from pydantic import ValidationError

from app.settings.config import Settings

pytestmark = pytest.mark.unit

_REQUIRED_ENV = {
    "DATABASE_URL": "postgresql+psycopg://user:pass@localhost/db",
    "KEYCLOAK_URL": "http://keycloak:8080",
    "KEYCLOAK_PUBLIC_URL": "http://localhost:8080",
    "KEYCLOAK_REALM": "fastapi-realm",
    "KEYCLOAK_CLIENT_ID": "fastapi-client",
    "KEYCLOAK_CLIENT_SECRET": "change-me",
}


@pytest.fixture(autouse=True)
def _mock_get_session(monkeypatch):
    async def _dummy_get_session():
        yield None

    monkeypatch.setattr("app.database.get_session", _dummy_get_session)


class TestSettings:
    def test_settings_requires_database_url(self, monkeypatch):
        for key in _REQUIRED_ENV:
            monkeypatch.delenv(key, raising=False)

        with pytest.raises(ValidationError):
            Settings(_env_file=None)  # ty: ignore[unknown-argument, missing-argument]

    def test_settings_defaults(self, monkeypatch):
        for key, value in _REQUIRED_ENV.items():
            monkeypatch.setenv(key, value)

        settings = Settings(_env_file=None)  # ty: ignore[unknown-argument, missing-argument]

        assert settings.app_name == "FastAPI Template"
        assert settings.port == 80
        assert settings.database_pool_size == 5
        assert settings.database_max_overflow == 10
        assert settings.database_echo is False
        assert settings.database_pool_pre_ping is True
        assert settings.keycloak_jwks_cache_ttl_minutes == 15
