from typing import Annotated

from fastapi import Depends, Request
from fastapi.openapi.models import OAuthFlowAuthorizationCode
from fastapi.openapi.models import OAuthFlows as OAuthFlowsModel
from fastapi.security import OAuth2
from fastapi.security.utils import get_authorization_scheme_param
from httpx import HTTPError
from jose import JWTError, jwt

from app.auth.jwks import get_public_key
from app.exceptions import AuthenticationError
from app.settings import settings

_oauth2_scheme = OAuth2(
    flows=OAuthFlowsModel(
        authorizationCode=OAuthFlowAuthorizationCode(
            authorizationUrl=(
                f"{settings.keycloak_public_url}/realms/{settings.keycloak_realm}"
                "/protocol/openid-connect/auth"
            ),
            tokenUrl=(
                f"{settings.keycloak_public_url}/realms/{settings.keycloak_realm}"
                "/protocol/openid-connect/token"
            ),
            scopes={"openid": "OpenID Connect"},
        )
    ),
    auto_error=False,
)


async def require_auth(
    request: Request,
    _: Annotated[str | None, Depends(_oauth2_scheme)],
) -> None:
    authorization = request.headers.get("Authorization")
    scheme, token = get_authorization_scheme_param(authorization)
    if not authorization or scheme.lower() != "bearer" or not token:
        raise AuthenticationError
    try:
        header = jwt.get_unverified_header(token)
        kid = header.get("kid")
        if kid is None:
            raise AuthenticationError
        key = await get_public_key(kid)
        if key is None:
            raise AuthenticationError
        jwt.decode(
            token,
            key,
            algorithms=["RS256"],
            options={"verify_aud": False},
            issuer=f"{settings.keycloak_public_url}/realms/{settings.keycloak_realm}",
        )
    except (JWTError, KeyError, HTTPError) as err:
        raise AuthenticationError from err
