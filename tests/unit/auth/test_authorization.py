import pytest

from app.auth import ENTITY_WRITE_ROLE, AuthClaims, require_role
from app.exceptions import ForbiddenError

pytestmark = pytest.mark.unit


def _claims(*roles: str) -> AuthClaims:
    return AuthClaims(
        sub="user-1",
        iss="https://idp.example",
        aud="api-client",
        exp=1_800_000_000,
        iat=1_799_996_400,
        nbf=1_799_996_400,
        roles=frozenset(roles),
    )


def test_require_role_returns_claims_when_the_role_is_present() -> None:
    claims = _claims(ENTITY_WRITE_ROLE, "reader")

    assert require_role(ENTITY_WRITE_ROLE)(claims) is claims


def test_require_role_rejects_claims_without_the_role() -> None:
    check = require_role(ENTITY_WRITE_ROLE)
    claims = _claims("reader")

    with pytest.raises(ForbiddenError) as exc_info:
        check(claims)

    assert exc_info.value.status_code == 403
    assert exc_info.value.message == f"Role '{ENTITY_WRITE_ROLE}' is required"
