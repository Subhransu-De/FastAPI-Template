from pydantic_settings import BaseSettings, SettingsConfigDict


class DatabaseSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_prefix="DATABASE_",
        extra="ignore",
    )

    url: str
    pool_size: int = 5
    max_overflow: int = 10
    echo: bool = False
    pool_pre_ping: bool = True


db_settings = DatabaseSettings()  # ty: ignore[missing-argument]
