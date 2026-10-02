import pytest
from fastapi import Depends

from app.auth import OIDCOpenAPIFastAPI, authenticate_request
from app.settings import Settings

pytestmark = pytest.mark.unit


def test_openapi_keeps_placeholders_until_discovery_runs(settings: Settings) -> None:
    app = OIDCOpenAPIFastAPI(settings=settings)

    @app.get("/protected", dependencies=[Depends(authenticate_request)])
    async def protected() -> None:
        return None

    flow = app.openapi()["components"]["securitySchemes"]["OIDC"]["flows"][
        "authorizationCode"
    ]

    assert flow["authorizationUrl"] == "about:blank"
    assert flow["tokenUrl"] == "about:blank"
