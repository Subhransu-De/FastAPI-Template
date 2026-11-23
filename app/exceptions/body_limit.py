from http import HTTPStatus

from starlette.datastructures import Headers
from starlette.requests import Request
from starlette.types import ASGIApp, Receive, Scope, Send

from app.exceptions.base import ProblemDetails, problem_response


class DeclaredBodyLimitMiddleware:
    """Reject a declared oversized body with Problem Details.

    FastAPI's `max_body_size` limiter answers a request whose `Content-Length`
    exceeds the limit with a plain-text 413, replacing any response the app
    renders. This middleware wraps FastAPI's stack and answers first, so the
    client gets the same Problem Details as for an oversized streamed body.
    """

    def __init__(self, app: ASGIApp, max_body_size: int | None) -> None:
        self.app = app
        self.max_body_size = max_body_size

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] == "http" and self._declares_oversized_body(scope):
            request = Request(scope)
            status = HTTPStatus.CONTENT_TOO_LARGE
            response = problem_response(
                ProblemDetails(
                    title=status.phrase,
                    status=status,
                    detail=status.phrase,
                    instance=str(request.url),
                )
            )
            await response(scope, receive, send)
            return
        await self.app(scope, receive, send)

    def _declares_oversized_body(self, scope: Scope) -> bool:
        if self.max_body_size is None:
            return False
        declared = Headers(scope=scope).get("content-length", "")
        return (
            declared.isascii()
            and declared.isdigit()
            and int(declared) > self.max_body_size
        )
