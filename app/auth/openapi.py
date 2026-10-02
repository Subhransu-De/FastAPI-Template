import json
from http import HTTPStatus
from typing import Any

from fastapi import FastAPI
from starlette.types import Lifespan

from app import telemetry
from app.auth.dependencies import OIDC_SCHEME_NAME
from app.exceptions import PROBLEM_JSON_MEDIA_TYPE, ProblemDetails
from app.settings import OIDCMetadata, Settings

_JSON_MEDIA_TYPE = "application/json"
_ERROR_STATUS_PREFIXES = ("4", "5")
_GENERATED_VALIDATION_STATUS = str(HTTPStatus.UNPROCESSABLE_CONTENT.value)
_GENERATED_VALIDATION_REF = "#/components/schemas/HTTPValidationError"
_GENERATED_VALIDATION_SCHEMAS = ("HTTPValidationError", "ValidationError")
_PROBLEM_DETAILS_REF = "#/components/schemas/ProblemDetails"
_VALIDATION_DESCRIPTION = "Validation Error"


def _use_problem_json_for_error_responses(schema: dict[str, Any]) -> None:
    for operations in schema.get("paths", {}).values():
        for operation in operations.values():
            for status, response in operation.get("responses", {}).items():
                if not str(status).startswith(_ERROR_STATUS_PREFIXES):
                    continue
                content = response.get("content", {})
                if _JSON_MEDIA_TYPE in content:
                    content[PROBLEM_JSON_MEDIA_TYPE] = content.pop(_JSON_MEDIA_TYPE)


def _is_generated_validation_response(response: dict[str, Any]) -> bool:
    return response == {
        "description": _VALIDATION_DESCRIPTION,
        "content": {
            PROBLEM_JSON_MEDIA_TYPE: {"schema": {"$ref": _GENERATED_VALIDATION_REF}}
        },
    }


def _add_problem_details(response: dict[str, Any]) -> None:
    problem_ref = {"$ref": _PROBLEM_DETAILS_REF}
    media = response.setdefault("content", {}).setdefault(PROBLEM_JSON_MEDIA_TYPE, {})
    declared = media.get("schema")
    alternatives = declared.get("anyOf", []) if isinstance(declared, dict) else []
    if declared is None:
        media["schema"] = problem_ref
    elif declared != problem_ref and problem_ref not in alternatives:
        media["schema"] = {"anyOf": [declared, problem_ref]}


def _drop_unreferenced_components(
    schema: dict[str, Any], names: tuple[str, ...]
) -> None:
    components = schema.get("components", {}).get("schemas", {})
    for name in names:
        if name in components and f'"#/components/schemas/{name}"' not in json.dumps(
            schema
        ):
            del components[name]


def _declare_validation_responses(schema: dict[str, Any], status: HTTPStatus) -> None:
    rewritten = False
    for operations in schema.get("paths", {}).values():
        for operation in operations.values():
            responses = operation.setdefault("responses", {})
            generated = responses.get(_GENERATED_VALIDATION_STATUS)
            if generated is not None and _is_generated_validation_response(generated):
                del responses[_GENERATED_VALIDATION_STATUS]
            elif not operation.get("parameters") and "requestBody" not in operation:
                continue
            rewritten = True
            declared = responses.get(str(status.value))
            if declared is None:
                declared = responses[str(status.value)] = {"description": status.phrase}
            elif "$ref" in declared:
                continue
            else:
                description = declared.get("description")
                declared["description"] = (
                    f"{description} or {_VALIDATION_DESCRIPTION}"
                    if description
                    else _VALIDATION_DESCRIPTION
                )
            _add_problem_details(declared)
    if not rewritten:
        return
    _drop_unreferenced_components(schema, _GENERATED_VALIDATION_SCHEMAS)
    schema.setdefault("components", {}).setdefault("schemas", {}).setdefault(
        "ProblemDetails", ProblemDetails.model_json_schema()
    )


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
        _declare_validation_responses(schema, self.validation_status)
        if self.oidc_metadata is not None:
            _use_discovered_oidc_endpoints(schema, self.oidc_metadata)
        return schema
