import json
from typing import cast

import pytest
from fastapi import Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import Response
from sqlalchemy.exc import OperationalError
from sqlalchemy.exc import TimeoutError as PoolTimeoutError
from starlette.exceptions import HTTPException

from app.exceptions import (
    AuthenticationError,
    BaseError,
    ForbiddenError,
    ProblemDetails,
    base_exception_handler,
    problem_responses,
)

pytestmark = pytest.mark.unit


def load_json_body(response: Response) -> dict[str, object]:
    body = response.body
    raw_body = body.tobytes() if isinstance(body, memoryview) else body
    return cast("dict[str, object]", json.loads(raw_body))


def make_request(path: str = "/entities") -> Request:
    return Request(
        {
            "type": "http",
            "http_version": "1.1",
            "method": "GET",
            "scheme": "https",
            "path": path,
            "raw_path": path.encode(),
            "query_string": b"",
            "headers": [],
            "server": ("testserver", 443),
            "client": ("client", 1234),
        }
    )


def test_base_error_builds_problem_details() -> None:
    request = make_request("/entities/123")
    error = BaseError("broken", status_code=418, title="Teapot")

    assert error.problem(request) == ProblemDetails(
        type="https://testserver/openapi.json",
        title="Teapot",
        status=418,
        detail="broken",
        instance="https://testserver/entities/123",
    )


def test_problem_responses_declare_the_problem_details_model() -> None:
    from http import HTTPStatus

    responses = problem_responses(HTTPStatus.NOT_FOUND, HTTPStatus.FORBIDDEN)

    assert responses == {
        404: {"model": ProblemDetails, "description": "Not Found"},
        403: {"model": ProblemDetails, "description": "Forbidden"},
    }


def test_handler_maps_validation_errors_to_unprocessable_content() -> None:
    request = make_request("/entities")
    exc = RequestValidationError(
        [
            {
                "type": "missing",
                "loc": ("body", "name"),
                "msg": "Field required",
                "input": None,
            }
        ]
    )

    response = base_exception_handler(request, exc)
    body = load_json_body(response)

    assert response.status_code == 422
    assert response.media_type == "application/problem+json"
    assert body["type"] == "https://testserver/openapi.json"
    assert body["title"] == "Unprocessable Content"
    assert body["status"] == 422
    assert body["instance"] == "https://testserver/entities"
    detail = cast("list[dict[str, object]]", body["detail"])
    assert detail[0]["type"] == "missing"
    assert detail[0]["loc"] == ["body", "name"]


def test_handler_maps_base_errors() -> None:
    request = make_request("/entities/123")
    exc = BaseError("not found", status_code=404, title="Not Found")

    response = base_exception_handler(request, exc)

    assert response.status_code == 404
    assert load_json_body(response) == {
        "type": "https://testserver/openapi.json",
        "title": "Not Found",
        "status": 404,
        "detail": "not found",
        "instance": "https://testserver/entities/123",
    }


def test_handler_keeps_authentication_challenge_headers() -> None:
    request = make_request("/entities")

    response = base_exception_handler(request, AuthenticationError())

    assert response.status_code == 401
    assert response.headers.get("www-authenticate") == "Bearer"
    assert response.media_type == "application/problem+json"
    assert load_json_body(response) == {
        "type": "https://testserver/openapi.json",
        "title": "Unauthorized",
        "status": 401,
        "detail": "Unauthorized",
        "instance": "https://testserver/entities",
    }


def test_handler_maps_forbidden_errors() -> None:
    response = base_exception_handler(make_request(), ForbiddenError("entities:write"))

    assert response.status_code == 403
    assert load_json_body(response)["detail"] == "Role 'entities:write' is required"


@pytest.mark.parametrize(
    "error",
    [
        pytest.param(
            OperationalError("SELECT 1", {}, ConnectionRefusedError()),
            id="connection-refused",
        ),
        pytest.param(PoolTimeoutError("QueuePool limit reached"), id="pool-timeout"),
    ],
)
def test_handler_maps_database_failures_to_service_unavailable(
    monkeypatch: pytest.MonkeyPatch,
    error: Exception,
) -> None:
    request = make_request("/entities")
    logged: list[tuple[tuple[object, ...], dict[str, object]]] = []

    def capture_log(*args: object, **kwargs: object) -> None:
        logged.append((args, kwargs))

    monkeypatch.setattr("app.exceptions.handlers.logfire.exception", capture_log)

    response = base_exception_handler(request, error)

    assert response.status_code == 503
    assert load_json_body(response) == {
        "type": "https://testserver/openapi.json",
        "title": "Service Unavailable",
        "status": 503,
        "detail": "The database is unavailable.",
        "instance": "https://testserver/entities",
    }
    assert logged == [
        (
            ("Database unavailable while processing {url}",),
            {"url": str(request.url), "_exc_info": error},
        )
    ]


def test_handler_hides_unexpected_error_details(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    request = make_request("/entities/123")
    error = RuntimeError("boom")
    logged: list[tuple[tuple[object, ...], dict[str, object]]] = []

    def capture_log(*args: object, **kwargs: object) -> None:
        logged.append((args, kwargs))

    monkeypatch.setattr("app.exceptions.handlers.logfire.exception", capture_log)

    response = base_exception_handler(request, error)

    assert response.status_code == 500
    assert response.media_type == "application/problem+json"
    assert logged == [
        (
            ("Unhandled exception while processing {url}",),
            {"url": str(request.url), "_exc_info": error},
        )
    ]
    assert load_json_body(response) == {
        "type": "about:blank",
        "title": "Internal Server Error",
        "status": 500,
        "detail": "An unexpected error occurred.",
        "instance": "https://testserver/entities/123",
    }


def test_handler_maps_framework_http_errors() -> None:
    request = make_request("/missing")

    response = base_exception_handler(request, HTTPException(status_code=404))

    assert response.status_code == 404
    assert response.media_type == "application/problem+json"
    assert load_json_body(response) == {
        "type": "about:blank",
        "title": "Not Found",
        "status": 404,
        "detail": "Not Found",
        "instance": "https://testserver/missing",
    }
