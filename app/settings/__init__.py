from typing import Self

from pydantic import BaseModel, ConfigDict

from app.settings.app import ApplicationSettings
from app.settings.authentication import (
    AuthNSettings,
    OIDCDiscoveryError,
    OIDCMetadata,
    resolve_oidc_metadata,
)
from app.settings.database import DatabaseSettings


class Settings(BaseModel):
    model_config = ConfigDict(frozen=True)

    app: ApplicationSettings
    database: DatabaseSettings
    oidc: AuthNSettings

    @classmethod
    def from_env(cls) -> Self:
        return cls(
            app=ApplicationSettings(),
            database=DatabaseSettings(),
            oidc=AuthNSettings(),
        )


__all__ = [
    "ApplicationSettings",
    "AuthNSettings",
    "DatabaseSettings",
    "OIDCDiscoveryError",
    "OIDCMetadata",
    "Settings",
    "resolve_oidc_metadata",
]
