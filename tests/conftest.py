import os

os.environ.setdefault(
    "DATABASE_URL", "postgresql+psycopg://user:pass@localhost:5432/test"
)
os.environ.setdefault("KEYCLOAK_URL", "http://keycloak:8080")
os.environ.setdefault("KEYCLOAK_PUBLIC_URL", "http://localhost:8080")
os.environ.setdefault("KEYCLOAK_REALM", "fastapi-realm")
os.environ.setdefault("KEYCLOAK_CLIENT_ID", "fastapi-client")
os.environ.setdefault("KEYCLOAK_CLIENT_SECRET", "change-me")
