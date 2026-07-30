from typing import TYPE_CHECKING, Annotated, cast

from fastapi import Depends, Request
from fastapi.security import OAuth2AuthorizationCodeBearer

from app.exceptions import AuthenticationError
from app.settings import authn_settings

if TYPE_CHECKING:
    from app.auth.token_validator import AccessTokenValidator

OIDC_SCHEME_NAME = "OIDC"

_oauth2_authorization_code = OAuth2AuthorizationCodeBearer(
    authorizationUrl=authn_settings.issuer_url,
    tokenUrl=authn_settings.issuer_url,
    scopes={"openid": "OpenID Connect"},
    scheme_name=OIDC_SCHEME_NAME,
    auto_error=False,
)


def authenticate_request(
    request: Request,
    access_token: Annotated[str | None, Depends(_oauth2_authorization_code)],
) -> None:
    if not access_token:
        raise AuthenticationError

    validator = cast(
        "AccessTokenValidator",
        request.app.state.access_token_validator,
    )
    request.state.access_token = access_token
    request.state.auth_claims = validator.validate(access_token)
