import json
import os
from http import HTTPStatus
from pathlib import Path

import pytest
from asgi_lifespan import LifespanManager

from app.exceptions import ErrorHandling
from app.main import create_app
from app.settings import Settings

pytestmark = pytest.mark.unit

SNAPSHOT_PATH = Path("tests/contract/openapi.json")
UPDATE_SNAPSHOT_ENV = "UPDATE_OPENAPI_SNAPSHOT"


def _render(schema: dict[str, object]) -> str:
    return json.dumps(schema, indent=2, sort_keys=True) + "\n"


def _assert_matches_snapshot(rendered: str) -> None:
    if os.environ.get(UPDATE_SNAPSHOT_ENV) == "1":
        SNAPSHOT_PATH.write_text(rendered, encoding="utf-8")

    assert SNAPSHOT_PATH.exists(), (
        f"Missing {SNAPSHOT_PATH}; run `make openapi-snapshot` to create it"
    )
    assert rendered == SNAPSHOT_PATH.read_text(encoding="utf-8"), (
        "OpenAPI document changed; review the diff and run `make openapi-snapshot`"
    )


async def test_openapi_document_matches_the_committed_contract(
    settings: Settings,
) -> None:
    app = create_app(settings)
    async with LifespanManager(app):
        rendered = _render(app.openapi())

    _assert_matches_snapshot(rendered)


async def test_openapi_document_declares_problem_details_for_error_responses(
    settings: Settings,
) -> None:
    app = create_app(settings)
    async with LifespanManager(app):
        schema = app.openapi()

    assert "ProblemDetails" in schema["components"]["schemas"]
    assert "HTTPValidationError" not in schema["components"]["schemas"]
    problem_ref = {"$ref": "#/components/schemas/ProblemDetails"}
    for path, operations in schema["paths"].items():
        for method, operation in operations.items():
            for status, response in operation["responses"].items():
                if not status.startswith(("4", "5")):
                    continue
                content = response["content"]["application/problem+json"]
                assert content["schema"] == problem_ref, (path, method, status)


async def test_openapi_document_declares_the_configured_validation_status(
    settings: Settings,
) -> None:
    app = create_app(settings, ErrorHandling(validation_status=HTTPStatus.BAD_REQUEST))
    async with LifespanManager(app):
        schema = app.openapi()

    create_responses = schema["paths"]["/entities/"]["post"]["responses"]
    assert "422" not in create_responses
    assert create_responses["400"] == {
        "content": {
            "application/problem+json": {
                "schema": {"$ref": "#/components/schemas/ProblemDetails"}
            }
        },
        "description": "Bad Request",
    }
