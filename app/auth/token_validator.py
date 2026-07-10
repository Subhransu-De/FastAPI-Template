from typing import Any

import jwt
from jwt import PyJWKClient, PyJWKClientError, PyJWTError

from app.exceptions import AuthenticationError
from app.settings import OIDCMetadata


class AccessTokenValidator:
    def __init__(
        self,
        metadata: OIDCMetadata,
        *,
        audience: str,
        jwks_cache_ttl_seconds: int,
    ) -> None:
        self._issuer = metadata.issuer
        self._audience = audience
        self._jwks_client = PyJWKClient(
            metadata.jwks_uri,
            cache_jwk_set=True,
            lifespan=jwks_cache_ttl_seconds,
        )

    def validate(self, token: str) -> dict[str, Any]:
        try:
            signing_key = self._jwks_client.get_signing_key_from_jwt(token)
            return jwt.decode(
                token,
                signing_key.key,
                algorithms=["RS256"],
                audience=self._audience,
                issuer=self._issuer,
                options={"require": ["exp", "iat", "nbf"]},
            )
        except (PyJWTError, PyJWKClientError) as error:
            raise AuthenticationError from error
