import httpx
import pytest
from pydantic import ValidationError

from app.settings import (
    ApplicationSettings,
    AuthNSettings,
    DatabaseSettings,
    Settings,
    resolve_oidc_metadata,
)

pytestmark = pytest.mark.unit

_DB_ENV = {"DATABASE_URL": "postgresql+psycopg://user:pass@localhost/db"}

_INTERNAL_OIDC_URL = "http://keycloak:8080/realms/fastapi-realm"

_OVERRIDE_KEYS = (
    "OIDC_JWKS_URI",
    "OIDC_ISSUER",
    "OIDC_AUTHORIZATION_ENDPOINT",
    "OIDC_TOKEN_ENDPOINT",
)

_AUTHN_ENV = {
    "OIDC_ISSUER_URL": "http://localhost:8080/realms/fastapi-realm",
    "OIDC_CLIENT_ID": "fastapi-client",
    "OIDC_DOCS_CLIENT_ID": "fastapi-docs",
    "OIDC_JWKS_URI": "http://localhost:8080/realms/fastapi-realm/protocol/openid-connect/certs",
    "OIDC_ISSUER": "http://localhost:8080/realms/fastapi-realm",
    "OIDC_AUTHORIZATION_ENDPOINT": "http://localhost:8080/realms/fastapi-realm/protocol/openid-connect/auth",
    "OIDC_TOKEN_ENDPOINT": "http://localhost:8080/realms/fastapi-realm/protocol/openid-connect/token",
}


def _set_env(monkeypatch: pytest.MonkeyPatch, env: dict[str, str]) -> None:
    for key in (*_AUTHN_ENV, *_DB_ENV, "OIDC_INTERNAL_URL"):
        monkeypatch.delenv(key, raising=False)
    for key, value in env.items():
        monkeypatch.setenv(key, value)


class TestApplicationSettings:
    def test_defaults(self) -> None:
        settings = ApplicationSettings(_env_file=None)

        assert settings.app_name == "FastAPI Template"
        assert settings.host == "127.0.0.1"
        assert settings.port == 80
        assert settings.reload is False
        assert settings.proxy_headers is False
        assert settings.forwarded_allow_ips == "127.0.0.1"

    def test_host_uses_app_host_env(self, monkeypatch: pytest.MonkeyPatch) -> None:
        docker_bind_host = "0.0.0.0"  # noqa: S104
        monkeypatch.setenv("APP_HOST", docker_bind_host)

        settings = ApplicationSettings(_env_file=None)

        assert settings.host == docker_bind_host

    def test_proxy_settings_come_from_env(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("PROXY_HEADERS", "true")
        monkeypatch.setenv("FORWARDED_ALLOW_IPS", "10.0.0.0/8")

        settings = ApplicationSettings(_env_file=None)

        assert settings.proxy_headers is True
        assert settings.forwarded_allow_ips == "10.0.0.0/8"


class TestDatabaseSettings:
    def test_requires_url(self, monkeypatch: pytest.MonkeyPatch) -> None:
        _set_env(monkeypatch, {})

        with pytest.raises(ValidationError):
            DatabaseSettings(_env_file=None)

    def test_defaults(self, monkeypatch: pytest.MonkeyPatch) -> None:
        _set_env(monkeypatch, _DB_ENV)

        settings = DatabaseSettings(_env_file=None)

        assert settings.url == _DB_ENV["DATABASE_URL"]
        assert settings.pool_size == 5
        assert settings.max_overflow == 10
        assert settings.echo is False
        assert settings.pool_pre_ping is True


class TestSettings:
    def test_from_env_composes_every_settings_group(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _set_env(monkeypatch, {**_DB_ENV, **_AUTHN_ENV})

        settings = Settings.from_env()

        assert settings.database.url == _DB_ENV["DATABASE_URL"]
        assert settings.oidc.client_id == _AUTHN_ENV["OIDC_CLIENT_ID"]
        assert settings.app.app_name == "FastAPI Template"


class TestAuthNSettings:
    def test_requires_fields(self, monkeypatch: pytest.MonkeyPatch) -> None:
        _set_env(monkeypatch, {})

        with pytest.raises(ValidationError):
            AuthNSettings(_env_file=None)

    def test_defaults(self, monkeypatch: pytest.MonkeyPatch) -> None:
        _set_env(monkeypatch, _AUTHN_ENV)

        settings = AuthNSettings(_env_file=None)

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

    async def test_resolves_discovery_when_overrides_are_not_set(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        env = {k: v for k, v in _AUTHN_ENV.items() if k not in _OVERRIDE_KEYS}
        _set_env(monkeypatch, env)

        discovery = {
            "jwks_uri": (
                "http://localhost:8080/realms/fastapi-realm/"
                "protocol/openid-connect/certs"
            ),
            "issuer": _AUTHN_ENV["OIDC_ISSUER_URL"],
            "authorization_endpoint": "http://localhost:8080/realms/fastapi-realm/auth",
            "token_endpoint": "http://localhost:8080/realms/fastapi-realm/token",
        }
        settings = AuthNSettings(_env_file=None)
        assert settings.metadata_override() is None

        def discovery_response(request: httpx.Request) -> httpx.Response:
            assert request.url.path.endswith("/.well-known/openid-configuration")
            return httpx.Response(200, json=discovery)

        transport = httpx.MockTransport(discovery_response)
        async with httpx.AsyncClient(transport=transport) as client:
            metadata = await resolve_oidc_metadata(settings, client=client)

        assert metadata.model_dump() == discovery

    async def test_internal_discovery_uses_internal_jwks_url(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        env = {
            "OIDC_ISSUER_URL": "http://localhost:8080/realms/fastapi-realm",
            "OIDC_INTERNAL_URL": _INTERNAL_OIDC_URL,
            "OIDC_CLIENT_ID": "fastapi-client",
            "OIDC_DOCS_CLIENT_ID": "fastapi-docs",
        }
        _set_env(monkeypatch, env)
        settings = AuthNSettings(_env_file=None)
        discovery = {
            "jwks_uri": f"{_INTERNAL_OIDC_URL}/protocol/openid-connect/certs",
            "issuer": env["OIDC_ISSUER_URL"],
            "authorization_endpoint": (
                "http://localhost:8080/realms/fastapi-realm/"
                "protocol/openid-connect/auth"
            ),
            "token_endpoint": f"{_INTERNAL_OIDC_URL}/protocol/openid-connect/token",
        }

        def discovery_response(request: httpx.Request) -> httpx.Response:
            assert request.url.host == "keycloak"
            return httpx.Response(200, json=discovery)

        async with httpx.AsyncClient(
            transport=httpx.MockTransport(discovery_response)
        ) as client:
            metadata = await resolve_oidc_metadata(settings, client=client)

        assert metadata.jwks_uri == discovery["jwks_uri"]
        assert metadata.authorization_endpoint == discovery["authorization_endpoint"]
        expected_endpoint = discovery["token_endpoint"].replace(
            "keycloak",
            "localhost",
        )
        assert metadata.token_endpoint == expected_endpoint

    async def test_blank_internal_url_is_treated_as_unset(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _set_env(
            monkeypatch,
            {
                "OIDC_ISSUER_URL": "https://idp.example/realm",
                "OIDC_INTERNAL_URL": "",
                "OIDC_CLIENT_ID": "fastapi-client",
                "OIDC_DOCS_CLIENT_ID": "fastapi-docs",
            },
        )
        settings = AuthNSettings(_env_file=None)
        discovery = {
            "jwks_uri": "https://idp.example/realm/jwks",
            "issuer": "https://idp.example/realm",
            "authorization_endpoint": "https://idp.example/realm/authorize",
            "token_endpoint": "https://idp.example/realm/token",
        }

        def discovery_response(request: httpx.Request) -> httpx.Response:
            assert request.url.host == "idp.example"
            return httpx.Response(200, json=discovery)

        async with httpx.AsyncClient(
            transport=httpx.MockTransport(discovery_response)
        ) as client:
            metadata = await resolve_oidc_metadata(settings, client=client)

        assert metadata.model_dump() == discovery

    def test_rejects_partial_endpoint_overrides(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _set_env(
            monkeypatch,
            {
                "OIDC_ISSUER_URL": _AUTHN_ENV["OIDC_ISSUER_URL"],
                "OIDC_CLIENT_ID": _AUTHN_ENV["OIDC_CLIENT_ID"],
                "OIDC_DOCS_CLIENT_ID": _AUTHN_ENV["OIDC_DOCS_CLIENT_ID"],
                "OIDC_JWKS_URI": _AUTHN_ENV["OIDC_JWKS_URI"],
            },
        )

        with pytest.raises(ValidationError, match="must provide"):
            AuthNSettings(_env_file=None)


def test_jwks_cache_ttl_must_be_positive(monkeypatch: pytest.MonkeyPatch) -> None:
    _set_env(monkeypatch, {**_AUTHN_ENV, "OIDC_JWKS_CACHE_TTL_SECONDS": "0"})

    with pytest.raises(ValidationError, match="greater than 0"):
        AuthNSettings(_env_file=None)
