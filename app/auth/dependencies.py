from typing import Annotated

from fastapi import Depends, Request
from fastapi.security import OAuth2AuthorizationCodeBearer

from app import telemetry
from app.auth.claims import AuthClaims
from app.auth.token_validator import AccessTokenValidator
from app.exceptions import AuthenticationError, MissingLifespanStateError

OIDC_SCHEME_NAME = "OIDC"
ACCESS_VALIDATOR_STATE_KEY = "access_validator"

_DISCOVERED_AT_STARTUP = "about:blank"

_oauth2_authorization_code = OAuth2AuthorizationCodeBearer(
    authorizationUrl=_DISCOVERED_AT_STARTUP,
    tokenUrl=_DISCOVERED_AT_STARTUP,
    scopes={"openid": "OpenID Connect"},
    scheme_name=OIDC_SCHEME_NAME,
    auto_error=False,
)


def get_token_validator(request: Request) -> AccessTokenValidator:
    try:
        validator = request.state.access_validator
    except AttributeError as error:
        raise MissingLifespanStateError(ACCESS_VALIDATOR_STATE_KEY) from error
    if not isinstance(validator, AccessTokenValidator):
        raise MissingLifespanStateError(ACCESS_VALIDATOR_STATE_KEY)
    return validator


def authenticate_request(
    request: Request,
    access_token: Annotated[str | None, Depends(_oauth2_authorization_code)],
    validator: Annotated[AccessTokenValidator, Depends(get_token_validator)],
) -> AuthClaims:
    if not access_token:
        raise AuthenticationError

    claims = validator.validate(access_token)
    telemetry.record_auth_attributes(
        request,
        telemetry.AuthAttributes(
            client_id=claims.azp,
            audience=claims.aud,
            issuer=claims.iss,
        ),
    )
    return claims
