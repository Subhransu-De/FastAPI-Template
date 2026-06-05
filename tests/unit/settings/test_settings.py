from unittest.mock import MagicMock, patch

import pytest
from pydantic import ValidationError

from app.settings import ApplicationSettings, AuthNSettings, DatabaseSettings

pytestmark = pytest.mark.unit

_DB_ENV = {"DATABASE_URL": "postgresql+psycopg://user:pass@localhost/db"}

_AUTHN_ENV = {
    "OIDC_ISSUER_URL": "http://localhost:8080/realms/fastapi-realm",
    "OIDC_CLIENT_ID": "fastapi-client",
    "OIDC_CLIENT_SECRET": "test-client-credential",
    "OIDC_JWKS_URI": "http://localhost:8080/realms/fastapi-realm/protocol/openid-connect/certs",
    "OIDC_ISSUER": "http://localhost:8080/realms/fastapi-realm",
    "OIDC_AUTHORIZATION_ENDPOINT": "http://localhost:8080/realms/fastapi-realm/protocol/openid-connect/auth",
    "OIDC_TOKEN_ENDPOINT": "http://localhost:8080/realms/fastapi-realm/protocol/openid-connect/token",
}


@pytest.fixture(autouse=True)
def _mock_get_session(monkeypatch):
    async def _dummy_get_session():
        yield None

    monkeypatch.setattr("app.database.get_session", _dummy_get_session)


class TestApplicationSettings:
    def test_defaults(self):
        settings = ApplicationSettings(_env_file=None)  # ty: ignore[unknown-argument]

        assert settings.app_name == "FastAPI Template"
        assert settings.port == 80
        assert settings.reload is False


class TestDatabaseSettings:
    def test_requires_url(self, monkeypatch):
        monkeypatch.delenv("DATABASE_URL", raising=False)

        with pytest.raises(ValidationError):
            DatabaseSettings(_env_file=None)  # ty: ignore[unknown-argument, missing-argument]

    def test_defaults(self, monkeypatch):
        for key, value in _DB_ENV.items():
            monkeypatch.setenv(key, value)

        settings = DatabaseSettings(_env_file=None)  # ty: ignore[unknown-argument, missing-argument]

        assert settings.url == _DB_ENV["DATABASE_URL"]
        assert settings.pool_size == 5
        assert settings.max_overflow == 10
        assert settings.echo is False
        assert settings.pool_pre_ping is True


class TestAuthNSettings:
    def test_requires_fields(self, monkeypatch):
        for key in _AUTHN_ENV:
            monkeypatch.delenv(key, raising=False)

        with pytest.raises(ValidationError):
            AuthNSettings(_env_file=None)  # ty: ignore[unknown-argument, missing-argument]

    def test_defaults(self, monkeypatch):
        for key, value in _AUTHN_ENV.items():
            monkeypatch.setenv(key, value)

        settings = AuthNSettings(_env_file=None)  # ty: ignore[unknown-argument, missing-argument]

        assert settings.issuer_url == _AUTHN_ENV["OIDC_ISSUER_URL"]
        assert settings.internal_url is None
        assert settings.client_id == _AUTHN_ENV["OIDC_CLIENT_ID"]
        assert settings.client_secret == _AUTHN_ENV["OIDC_CLIENT_SECRET"]
        assert settings.jwks_cache_ttl_seconds == 300
        assert settings.jwks_uri == _AUTHN_ENV["OIDC_JWKS_URI"]
        assert settings.issuer == _AUTHN_ENV["OIDC_ISSUER"]
        assert (
            settings.authorization_endpoint == _AUTHN_ENV["OIDC_AUTHORIZATION_ENDPOINT"]
        )
        assert settings.token_endpoint == _AUTHN_ENV["OIDC_TOKEN_ENDPOINT"]

    def test_fetches_discovery_when_jwks_uri_not_set(self, monkeypatch):
        env = {
            k: v
            for k, v in _AUTHN_ENV.items()
            if k
            not in (
                "OIDC_JWKS_URI",
                "OIDC_ISSUER",
                "OIDC_AUTHORIZATION_ENDPOINT",
                "OIDC_TOKEN_ENDPOINT",
            )
        }
        for key in (
            "OIDC_JWKS_URI",
            "OIDC_ISSUER",
            "OIDC_AUTHORIZATION_ENDPOINT",
            "OIDC_TOKEN_ENDPOINT",
        ):
            monkeypatch.delenv(key, raising=False)
        for key, value in env.items():
            monkeypatch.setenv(key, value)

        discovery = {
            "jwks_uri": "https://idp/certs",
            "issuer": "https://idp/realm",
            "authorization_endpoint": "https://idp/auth",
            "token_endpoint": "https://idp/token",
        }
        mock_response = MagicMock()
        mock_response.json.return_value = discovery

        with patch("app.settings.authentication.httpx.get", return_value=mock_response):
            settings = AuthNSettings(_env_file=None)  # ty: ignore[unknown-argument, missing-argument]

        assert settings.jwks_uri == discovery["jwks_uri"]
        assert settings.issuer == discovery["issuer"]
        assert settings.authorization_endpoint == discovery["authorization_endpoint"]
        assert settings.token_endpoint == discovery["token_endpoint"]
