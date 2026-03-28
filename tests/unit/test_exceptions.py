import json

import pytest
from fastapi import Request
from fastapi.exceptions import RequestValidationError

from app.exceptions.base import BaseError, base_exception_handler

pytestmark = pytest.mark.unit


def make_request(path: str = "/entities") -> Request:
    return Request(
        {
            "type": "http",
            "http_version": "1.1",
            "method": "GET",
            "scheme": "http",
            "path": path,
            "raw_path": path.encode(),
            "query_string": b"",
            "headers": [],
            "server": ("testserver", 80),
            "client": ("client", 1234),
        }
    )


def test_base_error_get_error():
    request = make_request("/entities/123")
    error = BaseError("broken", status_code=418, title="Teapot")

    payload = error.get_error(request)

    assert payload == {
        "type": "http://testserver/openapi.json",
        "title": "Teapot",
        "status": 418,
        "detail": "broken",
        "instance": "http://testserver/entities/123",
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
    body = json.loads(response.body)

    assert response.status_code == 400
    assert body["type"] == "http://testserver/openapi.json"
    assert body["title"] == "Bad Request"
    assert body["status"] == 400
    assert body["instance"] == "http://testserver/entities"
    assert isinstance(body["detail"], list)
    assert body["detail"][0]["type"] == "missing"


async def test_base_exception_handler_for_base_error():
    request = make_request("/entities/123")
    exc = BaseError("not found", status_code=404, title="Not Found")

    response = await base_exception_handler(request, exc)
    body = json.loads(response.body)

    assert response.status_code == 404
    assert body == {
        "type": "http://testserver/openapi.json",
        "title": "Not Found",
        "status": 404,
        "detail": "not found",
        "instance": "http://testserver/entities/123",
    }


async def test_base_exception_handler_for_unexpected_error(monkeypatch):
    request = make_request("/entities/123")
    error = RuntimeError("boom")
    logged = []

    monkeypatch.setattr("app.exceptions.base.logger.error", logged.append)

    response = await base_exception_handler(request, error)
    body = json.loads(response.body)

    assert response.status_code == 500
    assert logged == ["boom"]
    assert body == {
        "type": "about:blank",
        "title": "Internal Server Error",
        "status": 500,
        "detail": None,
        "instance": "http://testserver/entities/123",
    }
