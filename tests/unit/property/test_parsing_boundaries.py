import httpx
import pytest
from hypothesis import assume, given
from hypothesis import strategies as st

from app.auth import AuthClaims
from app.io.entity import EntityCreate
from app.settings import AuthNSettings, resolve_oidc_metadata

pytestmark = pytest.mark.unit

_alphabet = st.characters(exclude_categories=["Cs"])
_text = st.text(alphabet=_alphabet)
_segment = st.text(alphabet="abcdefghijklmnopqrstuvwxyz0123456789-", min_size=1)
_url_base = st.builds(
    lambda scheme, host, path: f"{scheme}://{host}/{'/'.join(path)}",
    st.sampled_from(["http", "https"]),
    _segment,
    st.lists(_segment, min_size=1, max_size=3),
)
_url_path = st.lists(_segment, min_size=1, max_size=3).map("/".join)
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


async def _discover_through_internal_url(
    issuer_url: str,
    internal_url: str,
    document: dict[str, str],
) -> dict[str, str]:
    settings = AuthNSettings(
        _env_file=None,
        issuer_url=issuer_url,
        internal_url=internal_url,
        client_id="api-client",
        docs_client_id="docs-client",
    )
    transport = httpx.MockTransport(lambda _: httpx.Response(200, json=document))
    async with httpx.AsyncClient(transport=transport) as client:
        metadata = await resolve_oidc_metadata(settings, client=client)
    return metadata.model_dump()


@given(issuer_url=_url_base, internal_url=_url_base, path=_url_path)
async def test_discovery_routes_jwks_inside_and_browser_endpoints_outside(
    issuer_url: str,
    internal_url: str,
    path: str,
) -> None:
    assume(issuer_url != internal_url)

    metadata = await _discover_through_internal_url(
        issuer_url,
        internal_url,
        {
            "issuer": issuer_url,
            "jwks_uri": f"{issuer_url}/{path}",
            "authorization_endpoint": f"{internal_url}/{path}",
            "token_endpoint": internal_url,
        },
    )

    assert metadata == {
        "issuer": issuer_url,
        "jwks_uri": f"{internal_url}/{path}",
        "authorization_endpoint": f"{issuer_url}/{path}",
        "token_endpoint": issuer_url,
    }


@given(issuer_url=_url_base, internal_url=_url_base, suffix=_segment)
async def test_discovery_leaves_urls_that_only_share_a_text_prefix(
    issuer_url: str,
    internal_url: str,
    suffix: str,
) -> None:
    assume(issuer_url != internal_url)
    document = {
        "issuer": issuer_url,
        "jwks_uri": f"{issuer_url}{suffix}/certs",
        "authorization_endpoint": f"{internal_url}{suffix}/auth",
        "token_endpoint": f"{internal_url}{suffix}",
    }

    metadata = await _discover_through_internal_url(issuer_url, internal_url, document)

    assert metadata == document
