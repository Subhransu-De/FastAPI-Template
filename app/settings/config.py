from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    app_name: str = "FastAPI Template"
    port: int = 80

    database_url: str
    database_pool_size: int = 5
    database_max_overflow: int = 10
    database_echo: bool = False
    database_pool_pre_ping: bool = True


settings = Settings()  # pyright: ignore[reportCallIssue]
