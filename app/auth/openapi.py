from typing import Any

from fastapi import FastAPI

from app.auth.dependencies import OIDC_SCHEME_NAME
from app.settings import OIDCMetadata


class OIDCOpenAPIFastAPI(FastAPI):
    def openapi(self) -> dict[str, Any]:
        schema = super().openapi()
        metadata = getattr(self.state, "oidc_metadata", None)
        if not isinstance(metadata, OIDCMetadata):
            return schema

        try:
            authorization_code = schema["components"]["securitySchemes"][
                OIDC_SCHEME_NAME
            ]["flows"]["authorizationCode"]
        except KeyError:
            return schema

        authorization_code["authorizationUrl"] = metadata.authorization_endpoint
        authorization_code["tokenUrl"] = metadata.token_endpoint
        return schema
