from functools import lru_cache
from typing import Annotated

import jwt
from fastapi import Depends, Request
from fastapi.openapi.models import OAuthFlowAuthorizationCode
from fastapi.openapi.models import OAuthFlows as OAuthFlowsModel
from fastapi.security import OAuth2
from fastapi.security.utils import get_authorization_scheme_param
from jwt import PyJWKClient, PyJWKClientError, PyJWTError

from app.exceptions import AuthenticationError
from app.settings import authn_settings

_oauth2_scheme = OAuth2(
    flows=OAuthFlowsModel(
        authorizationCode=OAuthFlowAuthorizationCode(
            authorizationUrl=authn_settings.authorization_endpoint,
            tokenUrl=authn_settings.token_endpoint,
            scopes={"openid": "OpenID Connect"},
        )
    ),
    auto_error=False,
)


@lru_cache
def _get_jwks_client() -> PyJWKClient:
    return PyJWKClient(
        authn_settings.jwks_uri,
        cache_jwk_set=True,
        lifespan=authn_settings.jwks_cache_ttl_seconds,
    )


def authentication_filter(
    request: Request,
    _: Annotated[str | None, Depends(_oauth2_scheme)],
) -> None:
    authorization = request.headers.get("Authorization")
    scheme, token = get_authorization_scheme_param(authorization)
    if not authorization or scheme.lower() != "bearer" or not token:
        raise AuthenticationError
    try:
        signing_key = _get_jwks_client().get_signing_key_from_jwt(token)
        claims = jwt.decode(
            token,
            signing_key.key,
            algorithms=["RS256"],
            audience=authn_settings.client_id,
            issuer=authn_settings.issuer,
            options={
                "require": ["exp", "iat", "nbf"],
            },
        )
        request.state.auth_claims = claims
    except (PyJWTError, PyJWKClientError) as err:
        raise AuthenticationError from err
