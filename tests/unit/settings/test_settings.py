import httpx
import pytest
from pydantic import ValidationError

from app.settings import (
    ApplicationSettings,
    AuthNSettings,
    DatabaseSettings,
    resolve_oidc_metadata,
)

pytestmark = pytest.mark.unit

_DB_ENV = {"DATABASE_URL": "postgresql+psycopg://user:pass@localhost/db"}

_AUTHN_ENV = {
    "OIDC_ISSUER_URL": "http://localhost:8080/realms/fastapi-realm",
    "OIDC_CLIENT_ID": "fastapi-client",
    "OIDC_DOCS_CLIENT_ID": "fastapi-docs",
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
        assert settings.host == "127.0.0.1"
        assert settings.port == 80
        assert settings.reload is False

    def test_host_uses_app_host_env(self, monkeypatch):
        docker_bind_host = "0.0.0.0"  # noqa: S104
        monkeypatch.setenv("APP_HOST", docker_bind_host)

        settings = ApplicationSettings(_env_file=None)  # ty: ignore[unknown-argument]

        assert settings.host == docker_bind_host


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
        assert settings.docs_client_id == _AUTHN_ENV["OIDC_DOCS_CLIENT_ID"]
        assert settings.jwks_cache_ttl_seconds == 300
        assert settings.jwks_uri == _AUTHN_ENV["OIDC_JWKS_URI"]
        assert settings.issuer == _AUTHN_ENV["OIDC_ISSUER"]
        assert (
            settings.authorization_endpoint == _AUTHN_ENV["OIDC_AUTHORIZATION_ENDPOINT"]
        )
        assert settings.token_endpoint == _AUTHN_ENV["OIDC_TOKEN_ENDPOINT"]

    async def test_resolves_discovery_when_overrides_are_not_set(self, monkeypatch):
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
            "jwks_uri": (
                "http://localhost:8080/realms/fastapi-realm/"
                "protocol/openid-connect/certs"
            ),
            "issuer": _AUTHN_ENV["OIDC_ISSUER_URL"],
            "authorization_endpoint": "http://localhost:8080/realms/fastapi-realm/auth",
            "token_endpoint": "http://localhost:8080/realms/fastapi-realm/token",
        }
        settings = AuthNSettings(_env_file=None)  # ty: ignore[unknown-argument, missing-argument]
        assert settings.metadata_override() is None

        def discovery_response(request: httpx.Request) -> httpx.Response:
            assert request.url.path.endswith("/.well-known/openid-configuration")
            return httpx.Response(200, json=discovery)

        transport = httpx.MockTransport(discovery_response)
        async with httpx.AsyncClient(transport=transport) as client:
            metadata = await resolve_oidc_metadata(settings, client=client)

        assert metadata.model_dump() == discovery

    async def test_internal_discovery_uses_internal_jwks_url(self, monkeypatch):
        env = {
            "OIDC_ISSUER_URL": "http://localhost:8080/realms/fastapi-realm",
            "OIDC_INTERNAL_URL": "http://keycloak:8080/realms/fastapi-realm",  # NOSONAR: local Compose-only URL
            "OIDC_CLIENT_ID": "fastapi-client",
            "OIDC_DOCS_CLIENT_ID": "fastapi-docs",
        }
        for key in _AUTHN_ENV:
            monkeypatch.delenv(key, raising=False)
        for key, value in env.items():
            monkeypatch.setenv(key, value)
        settings = AuthNSettings(_env_file=None)  # ty: ignore[unknown-argument, missing-argument]
        discovery = {
            "jwks_uri": (
                "http://keycloak:8080/realms/fastapi-realm/"  # NOSONAR: local Compose-only URL
                "protocol/openid-connect/certs"
            ),
            "issuer": env["OIDC_ISSUER_URL"],
            "authorization_endpoint": (
                "http://localhost:8080/realms/fastapi-realm/"
                "protocol/openid-connect/auth"
            ),
            "token_endpoint": (
                "http://keycloak:8080/realms/fastapi-realm/"  # NOSONAR: local Compose-only URL
                "protocol/openid-connect/token"
            ),
        }

        def discovery_response(request: httpx.Request) -> httpx.Response:
            assert request.url.host == "keycloak"
            return httpx.Response(200, json=discovery)

        async with httpx.AsyncClient(
            transport=httpx.MockTransport(discovery_response)
        ) as client:
            metadata = await resolve_oidc_metadata(settings, client=client)

        assert metadata.jwks_uri == (
            "http://keycloak:8080/realms/fastapi-realm/protocol/openid-connect/certs"  # NOSONAR: local Compose-only URL
        )
        assert metadata.authorization_endpoint == discovery["authorization_endpoint"]
        expected_endpoint = discovery["token_endpoint"].replace(
            "keycloak",
            "localhost",
        )
        assert metadata.token_endpoint == expected_endpoint

    def test_rejects_partial_endpoint_overrides(self, monkeypatch):
        for key in _AUTHN_ENV:
            monkeypatch.delenv(key, raising=False)
        monkeypatch.setenv("OIDC_ISSUER_URL", _AUTHN_ENV["OIDC_ISSUER_URL"])
        monkeypatch.setenv("OIDC_CLIENT_ID", _AUTHN_ENV["OIDC_CLIENT_ID"])
        monkeypatch.setenv("OIDC_DOCS_CLIENT_ID", _AUTHN_ENV["OIDC_DOCS_CLIENT_ID"])
        monkeypatch.setenv("OIDC_JWKS_URI", _AUTHN_ENV["OIDC_JWKS_URI"])

        with pytest.raises(ValidationError, match="must provide"):
            AuthNSettings(_env_file=None)  # ty: ignore[unknown-argument, missing-argument]
