import base64
import hashlib
import hmac
import json
import time
from collections.abc import AsyncGenerator, Callable, Iterator, Sequence
from os import environ
from typing import Any

import httpx
import jwt as pyjwt
import pytest
from alembic.config import Config
from asgi_lifespan import LifespanManager
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives.asymmetric.rsa import RSAPrivateKey
from cryptography.hazmat.primitives.serialization import (
    Encoding,
    NoEncryption,
    PrivateFormat,
    PublicFormat,
)
from jwt.algorithms import RSAAlgorithm
from pytest_httpserver import HTTPServer
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine
from testcontainers.community.postgres import PostgresContainer

from alembic import command
from app.auth import ENTITY_WRITE_ROLE, OIDCOpenAPIFastAPI
from app.database import SessionMaker, create_sessionmaker
from app.main import create_app
from app.model import Base
from app.settings import Settings
from tests.support import TEST_CLIENT_ID, TEST_ISSUER, build_settings

TEST_KID = "test-key-id"

WithAuth = pytest.mark.with_auth


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
def alembic_config(postgres_container: PostgresContainer) -> Config:
    cfg = Config("alembic.ini")
    cfg.set_main_option("script_location", "alembic")
    cfg.set_main_option(
        "sqlalchemy.url",
        postgres_container.get_connection_url(host="127.0.0.1"),
    )
    return cfg


@pytest.fixture(scope="session")
def test_postgres_url(alembic_config: Config) -> str:
    command.upgrade(alembic_config, "head")
    url = alembic_config.get_main_option("sqlalchemy.url")
    assert url is not None
    return url


@pytest.fixture
async def integration_engine(test_postgres_url: str) -> AsyncGenerator[AsyncEngine]:
    engine = create_async_engine(test_postgres_url, echo=False, pool_pre_ping=True)
    try:
        yield engine
    finally:
        await engine.dispose()


@pytest.fixture
def integration_sessionmaker(integration_engine: AsyncEngine) -> SessionMaker:
    return create_sessionmaker(integration_engine)


async def _clear_database(engine: AsyncEngine) -> None:
    async with engine.begin() as conn:
        for table in reversed(Base.metadata.sorted_tables):
            await conn.execute(table.delete())


@pytest.fixture
async def clean_integration_database(
    integration_engine: AsyncEngine,
) -> AsyncGenerator[None]:
    await _clear_database(integration_engine)
    yield
    await _clear_database(integration_engine)


@pytest.fixture(scope="session")
def signing_private_key() -> RSAPrivateKey:
    return rsa.generate_private_key(public_exponent=65537, key_size=2048)


@pytest.fixture(scope="session")
def foreign_private_key() -> RSAPrivateKey:
    return rsa.generate_private_key(public_exponent=65537, key_size=2048)


def build_jwks(private_key: RSAPrivateKey, kid: str = TEST_KID) -> dict[str, object]:
    jwk = json.loads(RSAAlgorithm.to_jwk(private_key.public_key()))
    jwk["kid"] = kid
    jwk["use"] = "sig"
    jwk["alg"] = "RS256"
    return {"keys": [jwk]}


@pytest.fixture(scope="session")
def _jwks_server(signing_private_key: RSAPrivateKey) -> Iterator[HTTPServer]:
    server = HTTPServer(host="127.0.0.1", port=0)
    server.start()
    server.expect_request("/jwks").respond_with_json(build_jwks(signing_private_key))
    yield server
    server.clear()
    server.stop()


def _private_pem(private_key: RSAPrivateKey) -> bytes:
    return private_key.private_bytes(
        encoding=Encoding.PEM,
        format=PrivateFormat.TraditionalOpenSSL,
        encryption_algorithm=NoEncryption(),
    )


def token_claims(
    *,
    audience: str = TEST_CLIENT_ID,
    issuer: str = TEST_ISSUER,
    expires_in_seconds: int = 3600,
    not_before_in_seconds: int = 0,
    roles: Sequence[str] = (ENTITY_WRITE_ROLE,),
) -> dict[str, object]:
    now = int(time.time())
    return {
        "sub": "test-user",
        "aud": audience,
        "iss": issuer,
        "azp": TEST_CLIENT_ID,
        "iat": now,
        "nbf": now + not_before_in_seconds,
        "exp": now + expires_in_seconds,
        "realm_access": {"roles": list(roles)},
    }


def make_test_token(
    private_key: RSAPrivateKey,
    *,
    kid: str = TEST_KID,
    **claims: Any,
) -> str:
    return pyjwt.encode(
        token_claims(**claims),
        _private_pem(private_key),
        algorithm="RS256",
        headers={"kid": kid},
    )


def make_unsigned_token(**claims: Any) -> str:
    return pyjwt.encode(
        token_claims(**claims),
        key="",
        algorithm="none",
        headers={"kid": TEST_KID},
    )


def _b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def make_hs256_token_signed_with_public_key(private_key: RSAPrivateKey) -> str:
    public_pem = private_key.public_key().public_bytes(
        Encoding.PEM, PublicFormat.SubjectPublicKeyInfo
    )
    header = _b64url(
        json.dumps({"alg": "HS256", "typ": "JWT", "kid": TEST_KID}).encode()
    )
    payload = _b64url(json.dumps(token_claims()).encode())
    signing_input = f"{header}.{payload}".encode()
    signature = hmac.new(public_pem, signing_input, hashlib.sha256).digest()
    return f"{header}.{payload}.{_b64url(signature)}"


@pytest.fixture
def token_factory(signing_private_key: RSAPrivateKey) -> Callable[..., str]:
    def factory(**claims: Any) -> str:
        return make_test_token(signing_private_key, **claims)

    return factory


@pytest.fixture
def integration_settings(test_postgres_url: str, _jwks_server: HTTPServer) -> Settings:
    return build_settings(
        database_url=test_postgres_url,
        jwks_uri=f"http://127.0.0.1:{_jwks_server.port}/jwks",
    )


@pytest.fixture
async def integration_app(
    integration_settings: Settings,
    clean_integration_database: None,
) -> AsyncGenerator[tuple[OIDCOpenAPIFastAPI, LifespanManager]]:
    app = create_app(integration_settings)
    async with LifespanManager(app) as manager:
        yield app, manager


@pytest.fixture
async def app_client(
    integration_app: tuple[OIDCOpenAPIFastAPI, LifespanManager],
    request: pytest.FixtureRequest,
    signing_private_key: RSAPrivateKey,
) -> AsyncGenerator[httpx.AsyncClient]:
    _, manager = integration_app
    headers: dict[str, str] = {}
    if request.node.get_closest_marker("with_auth"):
        headers["Authorization"] = f"Bearer {make_test_token(signing_private_key)}"

    transport = httpx.ASGITransport(app=manager.app)
    async with httpx.AsyncClient(
        transport=transport,
        base_url="https://testserver",
        headers=headers,
    ) as client:
        yield client
