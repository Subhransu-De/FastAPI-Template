from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class ScenarioTestSettings(BaseSettings):
    model_config = SettingsConfigDict(extra="ignore")

    target_base_url: str = Field(
        default="http://localhost",
        validation_alias="TARGET_BASE_URL",
    )
    token_url: str = Field(
        default="http://localhost:8080/realms/fastapi-e2e-realm/protocol/openid-connect/token",
        validation_alias="TOKEN_URL",
    )
    oidc_client_id: str = Field(
        default="fastapi-client",
        validation_alias="OIDC_CLIENT_ID",
    )
    oidc_client_secret: str = Field(validation_alias="OIDC_CLIENT_SECRET")
    username: str = Field(default="e2e-user", validation_alias="E2E_USERNAME")
    password: str = Field(validation_alias="E2E_PASSWORD")
    health_endpoint: str = Field(default="/health/db", validation_alias="HEALTH_ENDPOINT")

    @field_validator("target_base_url")
    @classmethod
    def strip_target_base_url_trailing_slash(cls, value: str) -> str:
        return value.rstrip("/")
