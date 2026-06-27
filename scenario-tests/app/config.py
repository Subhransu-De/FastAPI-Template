from pydantic import Field, ValidationInfo, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

REQUIRED_ENVIRONMENT_FIELDS = {
    "oidc_client_secret": "OIDC_CLIENT_SECRET",
    "password": "E2E_PASSWORD",
}


class ScenarioTestSettings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

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
    oidc_client_secret: str = Field(default="", validation_alias="OIDC_CLIENT_SECRET")
    username: str = Field(default="e2e-user", validation_alias="E2E_USERNAME")
    password: str = Field(default="", validation_alias="E2E_PASSWORD")
    health_endpoint: str = Field(default="/health/db", validation_alias="HEALTH_ENDPOINT")

    @field_validator("target_base_url")
    @classmethod
    def strip_target_base_url_trailing_slash(cls, value: str) -> str:
        return value.rstrip("/")

    @field_validator("oidc_client_secret", "password")
    @classmethod
    def require_environment_value(cls, value: str, info: ValidationInfo) -> str:
        if value:
            return value

        field_name = info.field_name
        if field_name is None:
            message = "Required environment value must be set"
            raise ValueError(message)

        environment_name = REQUIRED_ENVIRONMENT_FIELDS[field_name]
        message = f"{environment_name} must be set"
        raise ValueError(message)
