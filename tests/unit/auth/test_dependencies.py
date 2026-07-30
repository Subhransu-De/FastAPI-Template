from unittest.mock import Mock

import pytest
from fastapi import FastAPI, Request

from app.auth.dependencies import authenticate_request
from app.exceptions import AuthenticationError

pytestmark = pytest.mark.unit

_VALID_TOKEN = "valid.jwt.token"  # noqa: S105


def _make_request(validator: Mock) -> Request:
    app = FastAPI()
    app.state.access_token_validator = validator
    return Request({"type": "http", "app": app})


def test_authenticate_request_requires_an_access_token() -> None:
    request = _make_request(Mock())

    with pytest.raises(AuthenticationError):
        authenticate_request(request, None)


def test_authenticate_request_stores_validated_claims() -> None:
    validator = Mock()
    validator.validate.return_value = {"sub": "user-1"}
    request = _make_request(validator)

    authenticate_request(request, _VALID_TOKEN)

    validator.validate.assert_called_once_with(_VALID_TOKEN)
    assert request.state.access_token == _VALID_TOKEN
    assert request.state.auth_claims == {"sub": "user-1"}
