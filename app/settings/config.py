from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    app_name: str = "FastAPI Template"
    port: int = 80

settings = Settings()
