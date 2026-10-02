import pytest
from pydantic import ValidationError

from app.auth import AuthClaims

pytestmark = pytest.mark.unit

_BASE_PAYLOAD = {
    "sub": "user-1",
    "iss": "https://idp.example/realm",
    "aud": "api-client",
    "exp": 1_800_000_000,
    "iat": 1_799_996_400,
    "nbf": 1_799_996_400,
}


def test_claims_lift_keycloak_realm_roles() -> None:
    claims = AuthClaims.model_validate(
        {
            **_BASE_PAYLOAD,
            "azp": "docs-client",
            "realm_access": {"roles": ["entities:write", "offline_access"]},
            "email": "ignored@example.test",
        }
    )

    assert claims.azp == "docs-client"
    assert claims.roles == frozenset({"entities:write", "offline_access"})
    assert "email" not in claims.model_dump()


def test_claims_default_to_no_roles_without_realm_access() -> None:
    claims = AuthClaims.model_validate(_BASE_PAYLOAD)

    assert claims.roles == frozenset()
    assert claims.azp is None


def test_claims_keep_multiple_audiences() -> None:
    claims = AuthClaims.model_validate({**_BASE_PAYLOAD, "aud": ["api", "docs"]})

    assert claims.aud == ("api", "docs")


def test_claims_require_the_subject() -> None:
    payload = {key: value for key, value in _BASE_PAYLOAD.items() if key != "sub"}

    with pytest.raises(ValidationError):
        AuthClaims.model_validate(payload)
