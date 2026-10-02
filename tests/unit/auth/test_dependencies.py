import pytest
from fastapi import Request

from app import telemetry
from app.auth import (
    AccessTokenValidator,
    AuthClaims,
    authenticate_request,
    get_token_validator,
)
from app.exceptions import AuthenticationError, MissingLifespanStateError
from app.settings import OIDCMetadata

pytestmark = pytest.mark.unit

_VALID_TOKEN = "valid.jwt.token"  # noqa: S105
_METADATA = OIDCMetadata(
    jwks_uri="https://idp.example/jwks",
    issuer="https://idp.example",
    authorization_endpoint="https://idp.example/authorize",
    token_endpoint="https://idp.example/token",  # noqa: S106
)
_CLAIMS = AuthClaims(
    sub="user-1",
    iss=_METADATA.issuer,
    aud=("api-client", "docs-client"),
    azp="docs-client",
    exp=1_800_000_000,
    iat=1_799_996_400,
    nbf=1_799_996_400,
)


class _StubValidator(AccessTokenValidator):
    def __init__(self) -> None:
        super().__init__(
            _METADATA,
            audience="api-client",
            jwks_cache_ttl_seconds=60,
            jwks_refresh_cooldown_seconds=0,
        )
        self.tokens: list[str] = []

    def validate(self, token: str) -> AuthClaims:
        self.tokens.append(token)
        return _CLAIMS


def _request_with_state(**state: object) -> Request:
    return Request({"type": "http", "state": state})


def test_get_token_validator_reads_lifespan_state() -> None:
    validator = _StubValidator()

    assert get_token_validator(_request_with_state(access_validator=validator)) is (
        validator
    )


def test_get_token_validator_fails_when_lifespan_did_not_run() -> None:
    with pytest.raises(MissingLifespanStateError, match="access_validator"):
        get_token_validator(_request_with_state())


def test_get_token_validator_rejects_unexpected_state_values() -> None:
    with pytest.raises(MissingLifespanStateError, match="access_validator"):
        get_token_validator(_request_with_state(access_validator=object()))


def test_authenticate_request_requires_an_access_token() -> None:
    with pytest.raises(AuthenticationError):
        authenticate_request(_request_with_state(), None, _StubValidator())


def test_authenticate_request_returns_claims_and_records_telemetry() -> None:
    validator = _StubValidator()
    request = _request_with_state()

    claims = authenticate_request(request, _VALID_TOKEN, validator)

    assert claims is _CLAIMS
    assert validator.tokens == [_VALID_TOKEN]
    assert telemetry._auth_attributes(request) == telemetry.AuthAttributes(
        client_id="docs-client",
        audience=("api-client", "docs-client"),
        issuer=_METADATA.issuer,
    )
