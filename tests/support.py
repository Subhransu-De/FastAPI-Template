from app.settings import (
    ApplicationSettings,
    AuthNSettings,
    DatabaseSettings,
    Settings,
)

TEST_IDP_ORIGIN = "https://test-idp"
TEST_ISSUER = f"{TEST_IDP_ORIGIN}/realm"
TEST_CLIENT_ID = "test-client"
TEST_DOCS_CLIENT_ID = "test-docs"
TEST_AUTHORIZATION_ENDPOINT = "https://test-idp/authorize"
TEST_TOKEN_ENDPOINT = f"{TEST_IDP_ORIGIN}/token"
TEST_JWKS_URI = "https://test-idp/jwks"
TEST_APP_NAME = "FastAPI Template Test"
TEST_DATABASE_URL = "postgresql+psycopg://user:pass@localhost:5432/test"
UNREACHABLE_DATABASE_URL = "sqlite+aiosqlite:////nowhere/missing-directory/db.sqlite"


def build_settings(
    *,
    database_url: str = TEST_DATABASE_URL,
    jwks_uri: str = TEST_JWKS_URI,
    jwks_refresh_cooldown_seconds: int = 30,
) -> Settings:
    return Settings(
        app=ApplicationSettings(
            _env_file=None,
            app_name=TEST_APP_NAME,
            port=8000,
        ),
        database=DatabaseSettings(_env_file=None, url=database_url),
        oidc=AuthNSettings(
            _env_file=None,
            issuer_url=TEST_ISSUER,
            client_id=TEST_CLIENT_ID,
            docs_client_id=TEST_DOCS_CLIENT_ID,
            jwks_refresh_cooldown_seconds=jwks_refresh_cooldown_seconds,
            jwks_uri=jwks_uri,
            issuer=TEST_ISSUER,
            authorization_endpoint=TEST_AUTHORIZATION_ENDPOINT,
            token_endpoint=TEST_TOKEN_ENDPOINT,
        ),
    )
