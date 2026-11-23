from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

DEFAULT_MAX_BODY_SIZE = 1024 * 1024


class ApplicationSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_parse_none_str="null",
        extra="ignore",
    )

    app_name: str = "FastAPI Template"
    host: str = Field(default="127.0.0.1", validation_alias="APP_HOST")
    port: int = 80
    reload: bool = False
    proxy_headers: bool = False
    forwarded_allow_ips: str = "127.0.0.1"
    max_body_size: int | None = Field(
        default=1024 * 1024, ge=0, validation_alias="APP_MAX_BODY_SIZE"
    )
