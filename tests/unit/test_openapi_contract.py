import json
import os
from http import HTTPStatus
from pathlib import Path
from typing import Any

import pytest
from asgi_lifespan import LifespanManager
from pydantic import BaseModel

from app.exceptions import ErrorHandling, problem_responses
from app.main import create_app
from app.settings import Settings

pytestmark = pytest.mark.unit

SNAPSHOT_PATH = Path("tests/contract/openapi.json")
UPDATE_SNAPSHOT_ENV = "UPDATE_OPENAPI_SNAPSHOT"
PROBLEM_REF = {"$ref": "#/components/schemas/ProblemDetails"}
REASON = {"X-Reason": {"schema": {"type": "string"}}}


class ValidationError(BaseModel):
    reason: str


class Rejection(BaseModel):
    code: str


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


async def _schema_with_validation_status(
    settings: Settings, status: HTTPStatus
) -> dict[str, Any]:
    app = create_app(settings, ErrorHandling(validation_status=status))

    @app.post(
        "/probe",
        responses={
            **problem_responses(HTTPStatus.UNPROCESSABLE_CONTENT),
            400: {
                "description": "Flagged",
                "content": {"application/json": {"schema": True}},
            },
        },
    )
    async def probe(limit: int) -> None:
        del limit

    @app.get(
        "/probe/{item}",
        response_model=ValidationError,
        responses={
            400: {"model": Rejection, "description": "Rejected", "headers": REASON},
        },
    )
    async def probe_item(item: int) -> ValidationError:
        return ValidationError(reason=str(item))

    async with LifespanManager(app):
        return app.openapi()


async def test_openapi_document_declares_the_configured_validation_status(
    settings: Settings,
) -> None:
    schema = await _schema_with_validation_status(settings, HTTPStatus.BAD_REQUEST)

    create_responses = schema["paths"]["/entities/"]["post"]["responses"]
    assert "422" not in create_responses
    assert create_responses["400"] == {
        "content": {"application/problem+json": {"schema": PROBLEM_REF}},
        "description": "Bad Request",
    }
    probe_responses = schema["paths"]["/probe"]["post"]["responses"]
    assert "422" in probe_responses
    assert probe_responses["400"] == {
        "content": {
            "application/problem+json": {"schema": {"anyOf": [True, PROBLEM_REF]}}
        },
        "description": "Flagged or Validation Error",
    }


async def test_openapi_document_keeps_declarations_at_the_validation_status(
    settings: Settings,
) -> None:
    schema = await _schema_with_validation_status(settings, HTTPStatus.BAD_REQUEST)

    probe_responses = schema["paths"]["/probe/{item}"]["get"]["responses"]
    assert probe_responses["400"] == {
        "content": {
            "application/problem+json": {
                "schema": {
                    "anyOf": [
                        {"$ref": "#/components/schemas/Rejection"},
                        PROBLEM_REF,
                    ]
                }
            }
        },
        "description": "Rejected or Validation Error",
        "headers": REASON,
    }
    assert "ValidationError" in schema["components"]["schemas"]
    assert "HTTPValidationError" not in schema["components"]["schemas"]


async def test_openapi_document_merges_validation_into_a_declared_status(
    settings: Settings,
) -> None:
    schema = await _schema_with_validation_status(settings, HTTPStatus.NOT_FOUND)

    get_responses = schema["paths"]["/entities/{entity_id}"]["get"]["responses"]
    assert get_responses["404"] == {
        "content": {"application/problem+json": {"schema": PROBLEM_REF}},
        "description": "Not Found or Validation Error",
    }
