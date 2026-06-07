import asyncio
import json
import selectors
import sys
import time
from collections.abc import AsyncGenerator, Iterator
from os import environ
from typing import Any

import httpx
import jwt as pyjwt
import pytest
from alembic.config import Config
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives.asymmetric.rsa import RSAPrivateKey
from cryptography.hazmat.primitives.serialization import (
    Encoding,
    NoEncryption,
    PrivateFormat,
)
from jwt.algorithms import RSAAlgorithm
from pydantic_settings import BaseSettings, SettingsConfigDict
from pytest_httpserver import HTTPServer
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from testcontainers.postgres import PostgresContainer

from alembic import command
from app.model import Base
from app.settings.authentication import authn_settings

_TEST_ISSUER = "https://test-idp/realm"
_TEST_CLIENT_ID = "test-client"
_TEST_KID = "test-key-id"

WithAuth = pytest.mark.with_auth


class TestSettings(BaseSettings):
    model_config = SettingsConfigDict()

    app_name: str = "FastAPI Template Test"
    port: int = 8000

    database_url: str = "dummy://"
    database_pool_size: int = 5
    database_max_overflow: int = 10
    database_echo: bool = False
    database_pool_pre_ping: bool = True


@pytest.fixture
def test_settings() -> TestSettings:
    return TestSettings()


def selector_event_loop() -> asyncio.AbstractEventLoop:
    return asyncio.SelectorEventLoop(selectors.SelectSelector())


@pytest.fixture
def anyio_backend() -> str | tuple[str, dict[str, Any]]:
    if sys.platform == "win32":
        return "asyncio", {"loop_factory": selector_event_loop}
    return "asyncio"


@pytest.fixture(scope="session")
def postgres_container() -> Iterator[PostgresContainer]:
    with PostgresContainer(
        image="postgres:18-alpine",
        username="postgres",
        password=environ.get("INTEGRATION_TEST_CONTAINER_PASSWORD", "postgres"),
        dbname="fastapi_test",
        driver="psycopg",
    ) as container:
        yield container


@pytest.fixture(scope="session")
def test_postgres_url(postgres_container: PostgresContainer) -> str:
    database_url = postgres_container.get_connection_url(host="127.0.0.1")

    cfg = Config("alembic.ini")
    cfg.set_main_option("script_location", "alembic")
    cfg.set_main_option("sqlalchemy.url", database_url)
    command.upgrade(cfg, "head")

    return database_url


@pytest.fixture
async def integration_engine(test_postgres_url: str) -> AsyncGenerator[AsyncEngine]:
    engine = create_async_engine(test_postgres_url, echo=False, pool_pre_ping=True)
    try:
        yield engine
    finally:
        await engine.dispose()


@pytest.fixture
async def integration_sessionmaker(
    integration_engine: AsyncEngine,
) -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(
        bind=integration_engine,
        expire_on_commit=False,
        autocommit=False,
        autoflush=False,
    )


@pytest.fixture
async def clean_integration_database(
    integration_engine: AsyncEngine,
) -> AsyncGenerator[None]:
    yield

    async with integration_engine.begin() as conn:
        for table in reversed(Base.metadata.sorted_tables):
            await conn.execute(table.delete())


# --- Auth helpers ---


@pytest.fixture(scope="session")
def _rsa_private_key() -> RSAPrivateKey:
    return rsa.generate_private_key(public_exponent=65537, key_size=2048)


def _build_jwks(private_key: RSAPrivateKey) -> dict:
    jwk = json.loads(RSAAlgorithm.to_jwk(private_key.public_key()))
    jwk["kid"] = _TEST_KID
    jwk["use"] = "sig"
    jwk["alg"] = "RS256"
    return {"keys": [jwk]}


@pytest.fixture(scope="session")
def _jwks_server(_rsa_private_key: RSAPrivateKey) -> Iterator[HTTPServer]:
    server = HTTPServer(host="127.0.0.1", port=0)
    server.start()
    server.expect_request("/jwks").respond_with_json(_build_jwks(_rsa_private_key))
    yield server
    server.clear()
    server.stop()


@pytest.fixture(scope="session", autouse=True)
def _patch_authn_settings(_jwks_server: HTTPServer) -> Iterator[None]:
    original = (
        authn_settings.jwks_uri,
        authn_settings.issuer,
        authn_settings.client_id,
    )
    authn_settings.jwks_uri = f"http://127.0.0.1:{_jwks_server.port}/jwks"
    authn_settings.issuer = _TEST_ISSUER
    authn_settings.client_id = _TEST_CLIENT_ID
    yield
    authn_settings.jwks_uri, authn_settings.issuer, authn_settings.client_id = original


def _make_test_token(private_key: RSAPrivateKey) -> str:
    now = int(time.time())
    private_key_pem = private_key.private_bytes(
        encoding=Encoding.PEM,
        format=PrivateFormat.TraditionalOpenSSL,
        encryption_algorithm=NoEncryption(),
    )
    return pyjwt.encode(
        {
            "sub": "test-user",
            "aud": _TEST_CLIENT_ID,
            "iss": _TEST_ISSUER,
            "iat": now,
            "nbf": now,
            "exp": now + 3600,
        },
        private_key_pem,
        algorithm="RS256",
        headers={"kid": _TEST_KID},
    )


# --- App client ---


@pytest.fixture
async def app_client(
    integration_sessionmaker: async_sessionmaker[AsyncSession],
    clean_integration_database: None,
    request: pytest.FixtureRequest,
    _rsa_private_key: RSAPrivateKey,
) -> AsyncGenerator[httpx.AsyncClient]:
    from app.database import session as session_module
    from app.main import app

    async def override_get_session() -> AsyncGenerator[AsyncSession]:
        async with integration_sessionmaker() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise

    app.dependency_overrides[session_module.get_session] = override_get_session

    headers: dict[str, str] = {}
    if request.node.get_closest_marker("with_auth"):
        headers["Authorization"] = f"Bearer {_make_test_token(_rsa_private_key)}"

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(
        transport=transport,
        base_url="https://testserver",
        headers=headers,
    ) as client:
        yield client

    app.dependency_overrides.clear()
