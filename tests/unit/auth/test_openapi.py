from fastapi import Depends

from app.auth.dependencies import authenticate_request
from app.auth.openapi import OIDCOpenAPIFastAPI
from app.settings import OIDCMetadata


def test_oidc_openapi_uses_app_scoped_discovery_metadata() -> None:
    app = OIDCOpenAPIFastAPI()

    @app.get("/protected", dependencies=[Depends(authenticate_request)])
    async def protected() -> None:
        return None

    metadata = OIDCMetadata(
        jwks_uri="https://idp.example/jwks",
        issuer="https://idp.example",
        authorization_endpoint="https://idp.example/authorize",
        token_endpoint="https://idp.example/token",  # noqa: S106
    )
    app.state.oidc_metadata = metadata

    schema = app.openapi()
    authorization_code = schema["components"]["securitySchemes"]["OIDC"][
        "flows"
    ]["authorizationCode"]

    assert authorization_code["authorizationUrl"] == metadata.authorization_endpoint
    assert authorization_code["tokenUrl"] == metadata.token_endpoint
