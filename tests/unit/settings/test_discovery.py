from collections.abc import Callable

import httpx
import pytest

from app.settings import AuthNSettings, resolve_oidc_metadata
from app.settings import authentication as authentication_module

pytestmark = pytest.mark.unit

_ISSUER = "https://idp.example/realm"
_DISCOVERY = {
    "jwks_uri": f"{_ISSUER}/jwks",
    "issuer": _ISSUER,
    "authorization_endpoint": f"{_ISSUER}/authorize",
    "token_endpoint": f"{_ISSUER}/token",
}


@pytest.fixture
def discovery_settings() -> AuthNSettings:
    return AuthNSettings(
        _env_file=None,
        issuer_url=_ISSUER,
        client_id="api-client",
        docs_client_id="docs-client",
    )


@pytest.fixture
def sleeps(monkeypatch: pytest.MonkeyPatch) -> list[float]:
    recorded: list[float] = []

    async def fake_sleep(delay: float) -> None:
        recorded.append(delay)

    monkeypatch.setattr(authentication_module.asyncio, "sleep", fake_sleep)
    return recorded


def _client(
    responder: Callable[[int], httpx.Response],
) -> tuple[httpx.AsyncClient, list[int]]:
    attempts: list[int] = []

    def handler(request: httpx.Request) -> httpx.Response:
        attempts.append(len(attempts) + 1)
        return responder(len(attempts))

    return httpx.AsyncClient(transport=httpx.MockTransport(handler)), attempts


async def test_discovery_rejects_an_issuer_that_does_not_match_configuration(
    discovery_settings: AuthNSettings,
    sleeps: list[float],
) -> None:
    client, attempts = _client(
        lambda _: httpx.Response(200, json={**_DISCOVERY, "issuer": "https://other"})
    )

    async with client:
        with pytest.raises(RuntimeError, match="OIDC discovery failed") as exc_info:
            await resolve_oidc_metadata(discovery_settings, client=client)

    assert isinstance(exc_info.value.__cause__, ValueError)
    assert "does not match configured issuer" in str(exc_info.value.__cause__)
    assert attempts == [1, 2, 3]


async def test_discovery_retries_transient_failures_with_backoff(
    discovery_settings: AuthNSettings,
    sleeps: list[float],
) -> None:
    client, attempts = _client(
        lambda attempt: (
            httpx.Response(503) if attempt < 3 else httpx.Response(200, json=_DISCOVERY)
        )
    )

    async with client:
        metadata = await resolve_oidc_metadata(discovery_settings, client=client)

    assert metadata.model_dump() == _DISCOVERY
    assert attempts == [1, 2, 3]
    assert sleeps == [0.25, 0.5]


async def test_discovery_gives_up_after_the_configured_attempts(
    discovery_settings: AuthNSettings,
    sleeps: list[float],
) -> None:
    client, attempts = _client(lambda _: httpx.Response(500))

    async with client:
        with pytest.raises(RuntimeError) as exc_info:
            await resolve_oidc_metadata(discovery_settings, client=client, attempts=2)

    assert attempts == [1, 2]
    assert sleeps == [0.25]
    assert f"{_ISSUER}/.well-known/openid-configuration" in str(exc_info.value)
    assert isinstance(exc_info.value.__cause__, httpx.HTTPStatusError)


async def test_discovery_treats_incomplete_documents_as_failures(
    discovery_settings: AuthNSettings,
    sleeps: list[float],
) -> None:
    incomplete = {key: value for key, value in _DISCOVERY.items() if key != "jwks_uri"}
    client, attempts = _client(lambda _: httpx.Response(200, json=incomplete))

    async with client:
        with pytest.raises(RuntimeError) as exc_info:
            await resolve_oidc_metadata(discovery_settings, client=client)

    assert attempts == [1, 2, 3]
    assert isinstance(exc_info.value.__cause__, ValueError)


async def test_discovery_requires_at_least_one_attempt(
    discovery_settings: AuthNSettings,
) -> None:
    client, attempts = _client(lambda _: httpx.Response(200, json=_DISCOVERY))

    async with client:
        with pytest.raises(ValueError, match="at least 1"):
            await resolve_oidc_metadata(discovery_settings, client=client, attempts=0)

    assert attempts == []
