from http import HTTPStatus

from fastapi import Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse, Response
from starlette.exceptions import HTTPException

from app.logger import logger


class BaseError(Exception):
    def __init__(
        self,
        message: str,
        status_code: int = 500,
        title: str = "Internal Server Error",
        headers: dict[str, str] | None = None,
    ) -> None:
        self.message = message
        self.status_code = status_code
        self.title = title
        self.headers = headers
        super().__init__(message)

    def get_error(self, request: Request) -> dict:
        return {
            "type": f"{request.base_url}openapi.json",
            "title": self.title,
            "status": self.status_code,
            "detail": self.message,
            "instance": str(request.url),
        }


def base_exception_handler(request: Request, exc: Exception) -> Response:
    match exc:
        case RequestValidationError():
            return JSONResponse(
                status_code=400,
                content={
                    "type": f"{request.base_url}openapi.json",
                    "title": "Bad Request",
                    "status": 400,
                    "detail": exc.errors(),
                    "instance": str(request.url),
                },
                media_type="application/problem+json",
            )
        case BaseError():
            return JSONResponse(
                status_code=exc.status_code,
                content=exc.get_error(request),
                headers=exc.headers,
                media_type="application/problem+json",
            )
        case HTTPException():
            return JSONResponse(
                status_code=exc.status_code,
                content={
                    "type": "about:blank",
                    "title": _http_error_title(exc.status_code),
                    "status": exc.status_code,
                    "detail": exc.detail,
                    "instance": str(request.url),
                },
                headers=exc.headers,
                media_type="application/problem+json",
            )
        case _:
            logger.exception(
                "Unhandled exception while processing %s",
                request.url,
                exc=exc,
            )
            return JSONResponse(
                status_code=500,
                content={
                    "type": "about:blank",
                    "title": "Internal Server Error",
                    "status": 500,
                    "detail": "An unexpected error occurred.",
                    "instance": str(request.url),
                },
                media_type="application/problem+json",
            )


def _http_error_title(status_code: int) -> str:
    try:
        return HTTPStatus(status_code).phrase
    except ValueError:
        return "HTTP Error"
