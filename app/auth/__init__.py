from app.auth.authorization import ENTITY_WRITE_ROLE, require_role
from app.auth.claims import AuthClaims
from app.auth.dependencies import (
    ACCESS_VALIDATOR_STATE_KEY,
    authenticate_request,
    get_token_validator,
)
from app.auth.openapi import OIDCOpenAPIFastAPI
from app.auth.token_validator import AccessTokenValidator

__all__: list[str] = [
    "ACCESS_VALIDATOR_STATE_KEY",
    "ENTITY_WRITE_ROLE",
    "AccessTokenValidator",
    "AuthClaims",
    "OIDCOpenAPIFastAPI",
    "authenticate_request",
    "get_token_validator",
    "require_role",
]
