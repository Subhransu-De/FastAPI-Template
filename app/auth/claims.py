from collections.abc import Mapping

from pydantic import BaseModel, ConfigDict, model_validator

_REALM_ACCESS_CLAIM = "realm_access"
_ROLES_CLAIM = "roles"


class AuthClaims(BaseModel):
    model_config = ConfigDict(frozen=True, extra="ignore")

    sub: str
    iss: str
    aud: str | tuple[str, ...]
    exp: int
    iat: int
    nbf: int
    azp: str | None = None
    roles: frozenset[str] = frozenset()

    @model_validator(mode="before")
    @classmethod
    def _lift_realm_roles(cls, data: object) -> object:
        if not isinstance(data, Mapping) or _ROLES_CLAIM in data:
            return data
        realm_access = data.get(_REALM_ACCESS_CLAIM)
        if not isinstance(realm_access, Mapping):
            return data
        return {**data, _ROLES_CLAIM: realm_access.get(_ROLES_CLAIM, ())}
