import json
from typing import cast

import pytest
from fastapi import Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import Response
from starlette.exceptions import HTTPException

from app.exceptions.base import BaseError, base_exception_handler
from app.exceptions.exceptions import AuthenticationError

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


def test_base_error_get_error():
    request = make_request("/entities/123")
    error = BaseError("broken", status_code=418, title="Teapot")

    payload = error.get_error(request)

    assert payload == {
        "type": "https://testserver/openapi.json",
        "title": "Teapot",
        "status": 418,
        "detail": "broken",
        "instance": "https://testserver/entities/123",
    }


def test_base_exception_handler_for_validation_error():
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

    assert response.status_code == 400
    assert body["type"] == "https://testserver/openapi.json"
    assert body["title"] == "Bad Request"
    assert body["status"] == 400
    assert body["instance"] == "https://testserver/entities"
    detail = cast("list[dict[str, object]]", body["detail"])
    assert isinstance(detail, list)
    assert detail[0]["type"] == "missing"


def test_base_exception_handler_for_base_error():
    request = make_request("/entities/123")
    exc = BaseError("not found", status_code=404, title="Not Found")

    response = base_exception_handler(request, exc)
    body = load_json_body(response)

    assert response.status_code == 404
    assert body == {
        "type": "https://testserver/openapi.json",
        "title": "Not Found",
        "status": 404,
        "detail": "not found",
        "instance": "https://testserver/entities/123",
    }


def test_base_exception_handler_for_authentication_error():
    request = make_request("/entities")
    exc = AuthenticationError()

    response = base_exception_handler(request, exc)
    body = load_json_body(response)

    assert response.status_code == 401
    assert response.headers.get("www-authenticate") == "Bearer"
    assert response.media_type == "application/problem+json"
    assert body == {
        "type": "https://testserver/openapi.json",
        "title": "Unauthorized",
        "status": 401,
        "detail": "Unauthorized",
        "instance": "https://testserver/entities",
    }


def test_base_exception_handler_for_unexpected_error(monkeypatch):
    request = make_request("/entities/123")
    error = RuntimeError("boom")
    logged = []

    def capture_log(*args, **kwargs):
        logged.append((args, kwargs))

    monkeypatch.setattr("app.exceptions.base.logger.exception", capture_log)

    response = base_exception_handler(request, error)
    body = load_json_body(response)

    assert response.status_code == 500
    assert logged == [
        (
            ("Unhandled exception while processing %s", request.url),
            {"exc": error},
        )
    ]
    assert body == {
        "type": "about:blank",
        "title": "Internal Server Error",
        "status": 500,
        "detail": "An unexpected error occurred.",
        "instance": "https://testserver/entities/123",
    }
    assert response.media_type == "application/problem+json"


def test_base_exception_handler_for_framework_http_error():
    request = make_request("/missing")

    response = base_exception_handler(request, HTTPException(status_code=404))
    body = load_json_body(response)

    assert response.status_code == 404
    assert response.media_type == "application/problem+json"
    assert body == {
        "type": "about:blank",
        "title": "Not Found",
        "status": 404,
        "detail": "Not Found",
        "instance": "https://testserver/missing",
    }
