import asyncio
from typing import cast

import httpx
from pydantic import BaseModel, ConfigDict, model_validator
from pydantic.types import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

_DISCOVERY_PATH = "/.well-known/openid-configuration"
_DISCOVERY_ATTEMPTS = 3
_DISCOVERY_RETRY_DELAY_SECONDS = 0.25
_DISCOVERY_TIMEOUT = httpx.Timeout(5.0, connect=2.0)


class OIDCMetadata(BaseModel):
    model_config = ConfigDict(frozen=True)

    jwks_uri: str
    issuer: str
    authorization_endpoint: str
    token_endpoint: str


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
    client_secret: SecretStr
    docs_client_id: str
    jwks_cache_ttl_seconds: int = 300
    authorization_resource: str = "FastAPI API"
    authorization_timeout_seconds: int = 5

    # A complete override group bypasses discovery for tests and air-gapped runtimes.
    jwks_uri: str | None = None
    issuer: str | None = None
    authorization_endpoint: str | None = None
    token_endpoint: str | None = None

    @model_validator(mode="after")
    def _validate_endpoint_overrides(self) -> "AuthNSettings":
        overrides = (
            self.jwks_uri,
            self.issuer,
            self.authorization_endpoint,
            self.token_endpoint,
        )
        if any(overrides) and not all(overrides):
            message = (
                "OIDC endpoint overrides must provide JWKS_URI, ISSUER, "
                "AUTHORIZATION_ENDPOINT, and TOKEN_ENDPOINT together"
            )
            raise ValueError(message)
        return self

    def metadata_override(self) -> OIDCMetadata | None:
        if not self.jwks_uri:
            return None
        return OIDCMetadata(
            jwks_uri=self.jwks_uri,
            issuer=cast("str", self.issuer),
            authorization_endpoint=cast("str", self.authorization_endpoint),
            token_endpoint=cast("str", self.token_endpoint),
        )


def _replace_url_base(url: str, source_base: str, target_base: str) -> str:
    source = source_base.rstrip("/")
    target = target_base.rstrip("/")
    if url == source:
        return target
    if url.startswith(f"{source}/"):
        return f"{target}{url[len(source) :]}"
    return url


def _normalize_discovered_endpoints(
    metadata: OIDCMetadata,
    settings: AuthNSettings,
) -> OIDCMetadata:
    if not settings.internal_url:
        return metadata

    return metadata.model_copy(
        update={
            "jwks_uri": _replace_url_base(
                metadata.jwks_uri,
                settings.issuer_url,
                settings.internal_url,
            ),
            "authorization_endpoint": _replace_url_base(
                metadata.authorization_endpoint,
                settings.internal_url,
                settings.issuer_url,
            ),
            "token_endpoint": _replace_url_base(
                metadata.token_endpoint,
                settings.internal_url,
                settings.issuer_url,
            ),
        }
    )


def _validate_discovered_metadata(
    metadata: OIDCMetadata,
    settings: AuthNSettings,
) -> OIDCMetadata:
    if metadata.issuer != settings.issuer_url:
        message = (
            f"OIDC discovery issuer '{metadata.issuer}' does not match "
            f"configured issuer '{settings.issuer_url}'"
        )
        raise ValueError(message)
    return _normalize_discovered_endpoints(metadata, settings)


async def _discover_oidc_metadata(
    settings: AuthNSettings,
    client: httpx.AsyncClient,
    *,
    attempts: int,
    retry_delay_seconds: float,
) -> OIDCMetadata:
    discovery_base = settings.internal_url or settings.issuer_url
    discovery_url = f"{discovery_base.rstrip('/')}{_DISCOVERY_PATH}"
    last_error: Exception | None = None

    for attempt in range(1, attempts + 1):
        try:
            response = await client.get(discovery_url)
            response.raise_for_status()
            metadata = OIDCMetadata.model_validate(response.json())
            return _validate_discovered_metadata(metadata, settings)
        except (httpx.HTTPError, ValueError) as exc:
            last_error = exc
            if attempt < attempts:
                await asyncio.sleep(retry_delay_seconds * attempt)

    message = f"OIDC discovery failed after {attempts} attempts: {discovery_url}"
    raise RuntimeError(message) from last_error


async def resolve_oidc_metadata(
    settings: AuthNSettings,
    *,
    client: httpx.AsyncClient | None = None,
    attempts: int = _DISCOVERY_ATTEMPTS,
    retry_delay_seconds: float = _DISCOVERY_RETRY_DELAY_SECONDS,
) -> OIDCMetadata:
    if override := settings.metadata_override():
        return override
    if attempts < 1:
        message = "OIDC discovery attempts must be at least 1"
        raise ValueError(message)
    if client is not None:
        return await _discover_oidc_metadata(
            settings,
            client,
            attempts=attempts,
            retry_delay_seconds=retry_delay_seconds,
        )
    async with httpx.AsyncClient(timeout=_DISCOVERY_TIMEOUT) as discovery_client:
        return await _discover_oidc_metadata(
            settings,
            discovery_client,
            attempts=attempts,
            retry_delay_seconds=retry_delay_seconds,
        )


authn_settings = AuthNSettings()
