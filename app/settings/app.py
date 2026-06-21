from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class ApplicationSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    app_name: str = "FastAPI Template"
    host: str = Field(default="127.0.0.1", validation_alias="APP_HOST")
    port: int = 80
    reload: bool = False


app_settings = ApplicationSettings()
