from http import HTTPStatus
from typing import Any

from fastapi import FastAPI
from starlette.types import Lifespan

from app import telemetry
from app.auth.dependencies import OIDC_SCHEME_NAME
from app.exceptions import PROBLEM_JSON_MEDIA_TYPE
from app.settings import OIDCMetadata, Settings

_JSON_MEDIA_TYPE = "application/json"
_ERROR_STATUS_PREFIXES = ("4", "5")


def _use_problem_json_for_error_responses(schema: dict[str, Any]) -> None:
    for operations in schema.get("paths", {}).values():
        for operation in operations.values():
            for status, response in operation.get("responses", {}).items():
                if not str(status).startswith(_ERROR_STATUS_PREFIXES):
                    continue
                content = response.get("content", {})
                if _JSON_MEDIA_TYPE in content:
                    content[PROBLEM_JSON_MEDIA_TYPE] = content.pop(_JSON_MEDIA_TYPE)


def _declare_validation_status(schema: dict[str, Any], status: HTTPStatus) -> None:
    default = str(HTTPStatus.UNPROCESSABLE_CONTENT.value)
    for operations in schema.get("paths", {}).values():
        for operation in operations.values():
            responses = operation.get("responses", {})
            if default not in responses:
                continue
            response = responses.pop(default)
            response["description"] = status.phrase
            responses.setdefault(str(status.value), response)


def _use_discovered_oidc_endpoints(
    schema: dict[str, Any],
    metadata: OIDCMetadata,
) -> None:
    try:
        authorization_code = schema["components"]["securitySchemes"][OIDC_SCHEME_NAME][
            "flows"
        ]["authorizationCode"]
    except KeyError:
        return
    authorization_code["authorizationUrl"] = metadata.authorization_endpoint
    authorization_code["tokenUrl"] = metadata.token_endpoint


class OIDCOpenAPIFastAPI(FastAPI):
    def __init__(
        self,
        *,
        settings: Settings,
        lifespan: Lifespan["OIDCOpenAPIFastAPI"] | None = None,
        validation_status: HTTPStatus = HTTPStatus.UNPROCESSABLE_CONTENT,
    ) -> None:
        super().__init__(
            title=settings.app.app_name,
            lifespan=lifespan,
            telemetry=telemetry.native_telemetry_config(),
            swagger_ui_init_oauth={
                "clientId": settings.oidc.docs_client_id,
                "scopes": "openid",
                "usePkceWithAuthorizationCodeGrant": True,
            },
        )
        self.settings = settings
        self.validation_status = validation_status
        self.oidc_metadata: OIDCMetadata | None = None

    def openapi(self) -> dict[str, Any]:
        if self.openapi_schema is not None:
            return self.openapi_schema
        schema = super().openapi()
        _use_problem_json_for_error_responses(schema)
        if self.validation_status != HTTPStatus.UNPROCESSABLE_CONTENT:
            _declare_validation_status(schema, self.validation_status)
        if self.oidc_metadata is not None:
            _use_discovered_oidc_endpoints(schema, self.oidc_metadata)
        return schema
