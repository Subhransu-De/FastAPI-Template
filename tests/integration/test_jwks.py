from collections.abc import AsyncIterator, Iterator
from contextlib import asynccontextmanager

import httpx
import pytest
from asgi_lifespan import LifespanManager
from cryptography.hazmat.primitives.asymmetric.rsa import RSAPrivateKey
from pytest_httpserver import HTTPServer

from app.main import create_app
from tests.integration.conftest import build_jwks, make_test_token
from tests.support import build_settings

pytestmark = pytest.mark.integration


@pytest.fixture
def rotating_jwks_server(signing_private_key: RSAPrivateKey) -> Iterator[HTTPServer]:
    server = HTTPServer(host="127.0.0.1", port=0)
    server.start()
    server.expect_request("/jwks").respond_with_json(build_jwks(signing_private_key))
    yield server
    server.clear()
    server.stop()


@asynccontextmanager
async def _client(
    database_url: str,
    server: HTTPServer,
    *,
    refresh_cooldown_seconds: int,
) -> AsyncIterator[httpx.AsyncClient]:
    settings = build_settings(
        database_url=database_url,
        jwks_uri=f"http://127.0.0.1:{server.port}/jwks",
        jwks_refresh_cooldown_seconds=refresh_cooldown_seconds,
    )
    app = create_app(settings)
    async with LifespanManager(app) as manager:
        transport = httpx.ASGITransport(app=manager.app)
        async with httpx.AsyncClient(
            transport=transport, base_url="https://testserver"
        ) as client:
            yield client


def _serve(server: HTTPServer, jwks: dict[str, object]) -> None:
    server.clear_all_handlers()
    server.expect_request("/jwks").respond_with_json(jwks)


async def _status(client: httpx.AsyncClient, token: str) -> int:
    response = await client.get(
        "/entities/", headers={"Authorization": f"Bearer {token}"}
    )
    return response.status_code


async def test_key_rotation_is_picked_up_when_an_unknown_kid_arrives(
    test_postgres_url: str,
    clean_integration_database: None,
    rotating_jwks_server: HTTPServer,
    signing_private_key: RSAPrivateKey,
    foreign_private_key: RSAPrivateKey,
) -> None:
    old_token = make_test_token(signing_private_key)
    new_token = make_test_token(foreign_private_key, kid="rotated")

    async with _client(
        test_postgres_url, rotating_jwks_server, refresh_cooldown_seconds=0
    ) as client:
        assert await _status(client, old_token) == 200
        assert await _status(client, new_token) == 401

        _serve(rotating_jwks_server, build_jwks(foreign_private_key, kid="rotated"))

        assert await _status(client, new_token) == 200
        assert await _status(client, old_token) == 401


async def test_unknown_kids_do_not_cause_a_jwks_fetch_storm(
    test_postgres_url: str,
    clean_integration_database: None,
    rotating_jwks_server: HTTPServer,
    signing_private_key: RSAPrivateKey,
    foreign_private_key: RSAPrivateKey,
) -> None:
    async with _client(
        test_postgres_url, rotating_jwks_server, refresh_cooldown_seconds=30
    ) as client:
        assert await _status(client, make_test_token(signing_private_key)) == 200
        fetches_after_warmup = len(rotating_jwks_server.log)

        for kid in ("unknown-1", "unknown-2", "unknown-3"):
            token = make_test_token(foreign_private_key, kid=kid)
            assert await _status(client, token) == 401

    assert len(rotating_jwks_server.log) == fetches_after_warmup


async def test_identity_provider_errors_fail_closed_and_recover(
    test_postgres_url: str,
    clean_integration_database: None,
    rotating_jwks_server: HTTPServer,
    signing_private_key: RSAPrivateKey,
) -> None:
    token = make_test_token(signing_private_key)
    rotating_jwks_server.clear_all_handlers()
    rotating_jwks_server.expect_request("/jwks").respond_with_data(status=503)

    async with _client(
        test_postgres_url, rotating_jwks_server, refresh_cooldown_seconds=30
    ) as client:
        outage = await client.get(
            "/entities/", headers={"Authorization": f"Bearer {token}"}
        )
        assert outage.status_code == 401
        assert outage.headers["content-type"] == "application/problem+json"

        _serve(rotating_jwks_server, build_jwks(signing_private_key))

        assert await _status(client, token) == 200
