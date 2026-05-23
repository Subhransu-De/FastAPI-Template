import json
from typing import cast

import pytest
from fastapi import Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.exceptions.base import BaseError, base_exception_handler

pytestmark = pytest.mark.unit


def load_json_body(response: JSONResponse) -> dict[str, object]:
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


async def test_base_exception_handler_for_validation_error():
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

    response = await base_exception_handler(request, exc)
    body = load_json_body(response)

    assert response.status_code == 400
    assert body["type"] == "https://testserver/openapi.json"
    assert body["title"] == "Bad Request"
    assert body["status"] == 400
    assert body["instance"] == "https://testserver/entities"
    detail = cast("list[dict[str, object]]", body["detail"])
    assert isinstance(detail, list)
    assert detail[0]["type"] == "missing"


async def test_base_exception_handler_for_base_error():
    request = make_request("/entities/123")
    exc = BaseError("not found", status_code=404, title="Not Found")

    response = await base_exception_handler(request, exc)
    body = load_json_body(response)

    assert response.status_code == 404
    assert body == {
        "type": "https://testserver/openapi.json",
        "title": "Not Found",
        "status": 404,
        "detail": "not found",
        "instance": "https://testserver/entities/123",
    }


async def test_base_exception_handler_for_unexpected_error(monkeypatch):
    request = make_request("/entities/123")
    error = RuntimeError("boom")
    logged = []

    monkeypatch.setattr("app.exceptions.base.logger.error", logged.append)

    response = await base_exception_handler(request, error)
    body = load_json_body(response)

    assert response.status_code == 500
    assert logged == ["boom"]
    assert body == {
        "type": "about:blank",
        "title": "Internal Server Error",
        "status": 500,
        "detail": None,
        "instance": "https://testserver/entities/123",
    }
