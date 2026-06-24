from unittest.mock import MagicMock, patch

import pytest
from fastapi import Request
from jwt import PyJWKClientError, PyJWTError

from app.auth import authentication_filter
from app.auth.token_validator import _get_jwks_client
from app.exceptions.exceptions import AuthenticationError
from app.settings import authn_settings

pytestmark = pytest.mark.unit

_VALID_TOKEN = "valid.jwt.token"  # noqa: S105


def _make_request(authorization: str | None) -> Request:
    headers = {"authorization": authorization} if authorization else {}
    scope = {
        "type": "http",
        "method": "GET",
        "path": "/",
        "headers": [(k.encode(), v.encode()) for k, v in headers.items()],
    }
    return Request(scope)


class TestGetJwksClient:
    def test_returns_pyjwks_client_with_settings(self):
        with patch(
            "app.auth.token_validator.PyJWKClient", return_value=MagicMock()
        ) as mock_cls:
            client = _get_jwks_client()

        mock_cls.assert_called_once_with(
            authn_settings.jwks_uri,
            cache_jwk_set=True,
            lifespan=authn_settings.jwks_cache_ttl_seconds,
        )
        assert client is mock_cls.return_value


class TestAuthenticationFilter:
    def test_raises_when_no_authorization_header(self):
        request = _make_request(None)
        with pytest.raises(AuthenticationError):
            authentication_filter(request, None)

    def test_raises_when_scheme_is_not_bearer(self):
        request = _make_request("Basic dXNlcjpwYXNz")
        with pytest.raises(AuthenticationError):
            authentication_filter(request, None)

    def test_raises_when_token_is_empty(self):
        request = _make_request("Bearer ")
        with pytest.raises(AuthenticationError):
            authentication_filter(request, None)

    def test_raises_on_pyjwt_error(self):
        request = _make_request(f"Bearer {_VALID_TOKEN}")
        mock_signing_key = MagicMock()
        with (
            patch("app.auth.token_validator._get_jwks_client") as mock_get_client,
            patch(
                "app.auth.token_validator.jwt.decode",
                side_effect=PyJWTError("bad token"),
            ),
        ):
            mock_get_client.return_value.get_signing_key_from_jwt.return_value = (
                mock_signing_key
            )
            with pytest.raises(AuthenticationError):
                authentication_filter(request, None)

    def test_raises_on_pyjwkclient_error(self):
        request = _make_request(f"Bearer {_VALID_TOKEN}")
        with patch("app.auth.token_validator._get_jwks_client") as mock_get_client:
            mock_get_client.return_value.get_signing_key_from_jwt.side_effect = (
                PyJWKClientError("cannot fetch key")
            )
            with pytest.raises(AuthenticationError):
                authentication_filter(request, None)

    def test_succeeds_with_valid_token(self):
        request = _make_request(f"Bearer {_VALID_TOKEN}")
        mock_signing_key = MagicMock()
        with (
            patch("app.auth.token_validator._get_jwks_client") as mock_get_client,
            patch(
                "app.auth.token_validator.jwt.decode", return_value={"sub": "user-1"}
            ),
        ):
            mock_get_client.return_value.get_signing_key_from_jwt.return_value = (
                mock_signing_key
            )
            result = authentication_filter(request, None)
            assert result is None

    def test_authentication_error_is_chained_from_jwt_error(self):
        request = _make_request(f"Bearer {_VALID_TOKEN}")
        original_error = PyJWTError("expired")
        mock_signing_key = MagicMock()
        with (
            patch("app.auth.token_validator._get_jwks_client") as mock_get_client,
            patch("app.auth.token_validator.jwt.decode", side_effect=original_error),
        ):
            mock_get_client.return_value.get_signing_key_from_jwt.return_value = (
                mock_signing_key
            )
            with pytest.raises(AuthenticationError) as exc_info:
                authentication_filter(request, None)
            assert exc_info.value.__cause__ is original_error

    def test_authentication_error_is_chained_from_jwks_error(self):
        request = _make_request(f"Bearer {_VALID_TOKEN}")
        original_error = PyJWKClientError("no key found")
        with patch("app.auth.token_validator._get_jwks_client") as mock_get_client:
            mock_get_client.return_value.get_signing_key_from_jwt.side_effect = (
                original_error
            )
            with pytest.raises(AuthenticationError) as exc_info:
                authentication_filter(request, None)
            assert exc_info.value.__cause__ is original_error
