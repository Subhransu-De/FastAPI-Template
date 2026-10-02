import pytest
from hypothesis import given
from hypothesis import strategies as st

from app.auth import AuthClaims
from app.io.entity import EntityCreate

pytestmark = pytest.mark.unit

_alphabet = st.characters(exclude_categories=["Cs"])
_text = st.text(alphabet=_alphabet)
_base_claims = {
    "sub": "user-1",
    "iss": "https://idp.example/realm",
    "aud": "api-client",
    "exp": 1_800_000_000,
    "iat": 1_799_996_400,
    "nbf": 1_799_996_400,
}


@given(roles=st.lists(_text.filter(bool), max_size=8))
def test_realm_roles_always_lift_to_the_exact_role_set(roles: list[str]) -> None:
    claims = AuthClaims.model_validate(
        {**_base_claims, "realm_access": {"roles": roles}}
    )

    assert claims.roles == frozenset(roles)


@given(
    audience=st.one_of(
        _text.filter(bool),
        st.lists(_text.filter(bool), min_size=1, max_size=4),
    )
)
def test_audience_accepts_a_string_or_a_list(audience: str | list[str]) -> None:
    claims = AuthClaims.model_validate({**_base_claims, "aud": audience})

    expected = audience if isinstance(audience, str) else tuple(audience)
    assert claims.aud == expected


@given(realm_access=st.one_of(st.none(), st.integers(), _text, st.lists(_text)))
def test_non_mapping_realm_access_never_grants_roles(realm_access: object) -> None:
    claims = AuthClaims.model_validate({**_base_claims, "realm_access": realm_access})

    assert claims.roles == frozenset()


@given(
    name=_text.filter(lambda value: 1 <= len(value) <= 255),
    description=st.one_of(st.none(), _text.filter(lambda value: len(value) <= 5000)),
)
def test_entity_create_round_trips_through_json(
    name: str,
    description: str | None,
) -> None:
    payload = EntityCreate(name=name, description=description)

    assert EntityCreate.model_validate_json(payload.model_dump_json()) == payload
