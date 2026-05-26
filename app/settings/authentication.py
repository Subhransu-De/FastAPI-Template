import httpx
from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class AuthNSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_prefix="OIDC_",
        extra="ignore",
    )

    issuer_url: str
    internal_url: str | None = None
    client_id: str
    client_secret: str
    jwks_cache_ttl_seconds: int = 300

    # Populated from OIDC discovery on startup; can be overridden via env vars
    # (e.g. OIDC_JWKS_URI) to skip the HTTP fetch in tests or air-gapped envs.
    jwks_uri: str = ""
    issuer: str = ""
    authorization_endpoint: str = ""
    token_endpoint: str = ""

    @model_validator(mode="after")
    def _fetch_discovery(self) -> "AuthNSettings":
        if self.jwks_uri:
            return self
        base = self.internal_url or self.issuer_url
        resp = httpx.get(f"{base}/.well-known/openid-configuration")
        resp.raise_for_status()
        data = resp.json()
        self.jwks_uri = data["jwks_uri"]
        self.issuer = data["issuer"]
        self.authorization_endpoint = data["authorization_endpoint"]
        self.token_endpoint = data["token_endpoint"]
        return self


authn_settings = AuthNSettings()  # ty: ignore[missing-argument]
