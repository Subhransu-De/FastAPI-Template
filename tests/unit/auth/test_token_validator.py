from unittest.mock import MagicMock, patch

import pytest
from jwt import PyJWKClientError, PyJWTError

from app.auth.token_validator import AccessTokenValidator
from app.exceptions import AuthenticationError
from app.settings import OIDCMetadata

pytestmark = pytest.mark.unit

_VALID_TOKEN = "valid.jwt.token"  # noqa: S105
_METADATA = OIDCMetadata(
    jwks_uri="https://idp.example/jwks",
    issuer="https://idp.example",
    authorization_endpoint="https://idp.example/authorize",
    token_endpoint="https://idp.example/token",  # noqa: S106
)


def _create_validator() -> tuple[AccessTokenValidator, MagicMock]:
    with patch(
        "app.auth.token_validator.PyJWKClient",
        return_value=MagicMock(),
    ) as jwks_client_class:
        validator = AccessTokenValidator(
            _METADATA,
            audience="api-client",
            jwks_cache_ttl_seconds=600,
        )

    jwks_client_class.assert_called_once_with(
        _METADATA.jwks_uri,
        cache_jwk_set=True,
        lifespan=600,
    )
    return validator, jwks_client_class.return_value


def test_validate_returns_decoded_claims() -> None:
    validator, jwks_client = _create_validator()
    signing_key = MagicMock()
    jwks_client.get_signing_key_from_jwt.return_value = signing_key

    with patch(
        "app.auth.token_validator.jwt.decode",
        return_value={"sub": "user-1"},
    ) as decode:
        claims = validator.validate(_VALID_TOKEN)

    decode.assert_called_once_with(
        _VALID_TOKEN,
        signing_key.key,
        algorithms=["RS256"],
        audience="api-client",
        issuer=_METADATA.issuer,
        options={"require": ["exp", "iat", "nbf"]},
    )
    assert claims == {"sub": "user-1"}


@pytest.mark.parametrize(
    "error",
    [PyJWTError("expired"), PyJWKClientError("no signing key")],
)
def test_validate_translates_jwt_errors(error: Exception) -> None:
    validator, jwks_client = _create_validator()
    jwks_client.get_signing_key_from_jwt.side_effect = error

    with pytest.raises(AuthenticationError) as exc_info:
        validator.validate(_VALID_TOKEN)

    assert exc_info.value.__cause__ is error


def test_validate_translates_decode_errors() -> None:
    validator, jwks_client = _create_validator()
    jwks_client.get_signing_key_from_jwt.return_value = MagicMock()
    error = PyJWTError("invalid claims")

    with (
        patch("app.auth.token_validator.jwt.decode", side_effect=error),
        pytest.raises(AuthenticationError) as exc_info,
    ):
        validator.validate(_VALID_TOKEN)

    assert exc_info.value.__cause__ is error
