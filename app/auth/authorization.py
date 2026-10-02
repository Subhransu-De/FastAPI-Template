from collections.abc import Callable
from typing import Annotated

from fastapi import Depends

from app.auth.claims import AuthClaims
from app.auth.dependencies import authenticate_request
from app.exceptions import ForbiddenError

ENTITY_WRITE_ROLE = "entities:write"


def require_role(role: str) -> Callable[[AuthClaims], AuthClaims]:
    def dependency(
        claims: Annotated[AuthClaims, Depends(authenticate_request)],
    ) -> AuthClaims:
        if role not in claims.roles:
            raise ForbiddenError(role)
        return claims

    return dependency
