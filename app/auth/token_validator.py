import jwt
from jwt import PyJWKClient, PyJWKClientError, PyJWTError
from pydantic import ValidationError

from app.auth.claims import AuthClaims
from app.exceptions import AuthenticationError
from app.settings import OIDCMetadata


class AccessTokenValidator:
    def __init__(
        self,
        metadata: OIDCMetadata,
        *,
        audience: str,
        jwks_cache_ttl_seconds: int,
        jwks_refresh_cooldown_seconds: int,
    ) -> None:
        self._issuer = metadata.issuer
        self._audience = audience
        self._jwks_client = PyJWKClient(
            metadata.jwks_uri,
            cache_jwk_set=True,
            lifespan=jwks_cache_ttl_seconds,
            cooldown_duration=jwks_refresh_cooldown_seconds,
        )

    def validate(self, token: str) -> AuthClaims:
        try:
            signing_key = self._jwks_client.get_signing_key_from_jwt(token)
            payload = jwt.decode(
                token,
                signing_key.key,
                algorithms=["RS256"],
                audience=self._audience,
                issuer=self._issuer,
                options={"require": ["exp", "iat", "nbf"]},
            )
            return AuthClaims.model_validate(payload)
        except (PyJWTError, PyJWKClientError, ValidationError) as error:
            raise AuthenticationError from error
