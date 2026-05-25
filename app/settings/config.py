from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    app_name: str = "FastAPI Template"
    port: int = 80

    database_url: str
    database_pool_size: int = 5
    database_max_overflow: int = 10
    database_echo: bool = False
    database_pool_pre_ping: bool = True

    keycloak_url: str
    keycloak_public_url: str
    keycloak_realm: str
    keycloak_client_id: str
    keycloak_client_secret: str
    keycloak_jwks_cache_ttl_minutes: int = 15


settings = Settings()  # ty: ignore[missing-argument]
