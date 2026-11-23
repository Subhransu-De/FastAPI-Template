import pytest
from starlette.types import Message, Receive, Scope, Send

from app.exceptions import DeclaredBodyLimitMiddleware

pytestmark = pytest.mark.unit


async def _ok(_scope: Scope, _receive: Receive, send: Send) -> None:
    await send({"type": "http.response.start", "status": 200, "headers": []})
    await send({"type": "http.response.body", "body": b""})


async def _no_body() -> Message:
    return {"type": "http.request", "body": b"", "more_body": False}


async def _status_for(content_length: bytes, max_body_size: int | None) -> int:
    sent: list[Message] = []

    async def send(message: Message) -> None:
        sent.append(message)

    scope: Scope = {
        "type": "http",
        "method": "POST",
        "scheme": "https",
        "server": ("testserver", 443),
        "path": "/entities/",
        "root_path": "",
        "query_string": b"",
        "headers": [(b"content-length", content_length)],
    }
    await DeclaredBodyLimitMiddleware(_ok, max_body_size)(scope, _no_body, send)
    return sent[0]["status"]


@pytest.mark.parametrize(
    ("content_length", "max_body_size", "expected"),
    [
        pytest.param(b"17", 16, 413, id="over-the-limit"),
        pytest.param(b"16", 16, 200, id="at-the-limit"),
        pytest.param(b"17", None, 200, id="unlimited"),
        pytest.param(b"\xb2", 0, 200, id="non-ascii-digit"),
        pytest.param(b"-1", 0, 200, id="not-a-length"),
    ],
)
async def test_declared_body_limit_only_rejects_parseable_oversized_lengths(
    content_length: bytes,
    max_body_size: int | None,
    expected: int,
) -> None:
    assert await _status_for(content_length, max_body_size) == expected
