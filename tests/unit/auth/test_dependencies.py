import logfire
import pytest
from fastapi import Request
from logfire.testing import CaptureLogfire

from app.auth import (
    AccessTokenValidator,
    AuthClaims,
    authenticate_request,
    get_token_validator,
)
from app.exceptions import AuthenticationError, MissingLifespanStateError
from app.settings import OIDCMetadata

pytestmark = pytest.mark.unit

_ENCODED_JWT = "valid.jwt.token"
_IDP_ORIGIN = "https://idp.example"
_METADATA = OIDCMetadata(
    jwks_uri="https://idp.example/jwks",
    issuer="https://idp.example",
    authorization_endpoint="https://idp.example/authorize",
    token_endpoint=f"{_IDP_ORIGIN}/token",
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
    request = _request_with_state()

    with pytest.raises(MissingLifespanStateError, match="access_validator"):
        get_token_validator(request)


def test_get_token_validator_rejects_unexpected_state_values() -> None:
    request = _request_with_state(access_validator=object())

    with pytest.raises(MissingLifespanStateError, match="access_validator"):
        get_token_validator(request)


def test_authenticate_request_requires_an_access_token() -> None:
    validator = _StubValidator()

    with pytest.raises(AuthenticationError):
        authenticate_request(None, validator)


def test_authenticate_request_returns_claims_and_tags_the_request_span(
    capfire: CaptureLogfire,
) -> None:
    validator = _StubValidator()

    with logfire.span("request"):
        claims = authenticate_request(_ENCODED_JWT, validator)

    assert claims is _CLAIMS
    assert validator.tokens == [_ENCODED_JWT]
    (span,) = capfire.exporter.exported_spans_as_dict()
    assert span["attributes"]["oidc.client_id"] == "docs-client"
    assert span["attributes"]["oidc.audience"] == ("api-client", "docs-client")
    assert span["attributes"]["oidc.issuer"] == _METADATA.issuer
