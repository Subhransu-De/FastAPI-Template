import os

os.environ.setdefault(
    "DATABASE_URL", "postgresql+psycopg://user:pass@localhost:5432/test"
)
os.environ.setdefault("OIDC_ISSUER_URL", "http://localhost:8080/realms/fastapi-realm")
os.environ.setdefault("OIDC_CLIENT_ID", "fastapi-client")
os.environ.setdefault("OIDC_CLIENT_SECRET", "test-client-credential")
os.environ.setdefault(
    "OIDC_JWKS_URI",
    "http://localhost:8080/realms/fastapi-realm/protocol/openid-connect/certs",
)
os.environ.setdefault("OIDC_ISSUER", "http://localhost:8080/realms/fastapi-realm")
os.environ.setdefault(
    "OIDC_AUTHORIZATION_ENDPOINT",
    "http://localhost:8080/realms/fastapi-realm/protocol/openid-connect/auth",
)
os.environ.setdefault(
    "OIDC_TOKEN_ENDPOINT",
    "http://localhost:8080/realms/fastapi-realm/protocol/openid-connect/token",
)
