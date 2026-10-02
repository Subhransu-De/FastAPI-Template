from unittest.mock import MagicMock, patch

import pytest
from jwt import PyJWKClientError, PyJWTError

from app.auth import AccessTokenValidator, AuthClaims
from app.exceptions import AuthenticationError
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
_PAYLOAD = {
    "sub": "user-1",
    "iss": _METADATA.issuer,
    "aud": "api-client",
    "azp": "api-client",
    "exp": 1_800_000_000,
    "iat": 1_799_996_400,
    "nbf": 1_799_996_400,
    "realm_access": {"roles": ["entities:write"]},
}


def _create_validator() -> tuple[AccessTokenValidator, MagicMock]:
    with patch(
        "app.auth.token_validator.PyJWKClient",
        return_value=MagicMock(),
    ) as jwks_client_class:
        validator = AccessTokenValidator(
            _METADATA,
            audience="api-client",
            jwks_cache_ttl_seconds=600,
            jwks_refresh_cooldown_seconds=15,
        )

    jwks_client_class.assert_called_once_with(
        _METADATA.jwks_uri,
        cache_jwk_set=True,
        lifespan=600,
        cooldown_duration=15,
    )
    return validator, jwks_client_class.return_value


def test_validate_returns_typed_claims() -> None:
    validator, jwks_client = _create_validator()
    jwks_client.get_signing_key_from_jwt.return_value = MagicMock()

    with patch("app.auth.token_validator.jwt.decode", return_value=_PAYLOAD):
        claims = validator.validate(_ENCODED_JWT)

    assert claims == AuthClaims.model_validate(_PAYLOAD)
    assert claims.roles == frozenset({"entities:write"})


def test_validate_rejects_tokens_without_required_claims() -> None:
    validator, jwks_client = _create_validator()
    jwks_client.get_signing_key_from_jwt.return_value = MagicMock()

    with (
        patch("app.auth.token_validator.jwt.decode", return_value={"aud": "x"}),
        pytest.raises(AuthenticationError),
    ):
        validator.validate(_ENCODED_JWT)


@pytest.mark.parametrize(
    "error",
    [PyJWTError("expired"), PyJWKClientError("no signing key")],
)
def test_validate_translates_jwt_errors(error: Exception) -> None:
    validator, jwks_client = _create_validator()
    jwks_client.get_signing_key_from_jwt.side_effect = error

    with pytest.raises(AuthenticationError) as exc_info:
        validator.validate(_ENCODED_JWT)

    assert exc_info.value.__cause__ is error
