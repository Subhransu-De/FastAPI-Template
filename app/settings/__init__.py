from pydantic import BaseModel, ConfigDict

from app.settings.app import ApplicationSettings
from app.settings.authentication import (
    AuthNSettings,
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
    def from_env(cls) -> "Settings":
        return cls(
            app=ApplicationSettings(),
            database=DatabaseSettings(),
            oidc=AuthNSettings(),
        )


__all__ = [
    "ApplicationSettings",
    "AuthNSettings",
    "DatabaseSettings",
    "OIDCMetadata",
    "Settings",
    "resolve_oidc_metadata",
]
