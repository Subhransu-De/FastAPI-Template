from fastapi import Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.logger import logger


class BaseException(Exception):
    def __init__(
        self, message: str, status_code: int = 500, title: str = "Internal Server Error"
    ):
        self.message = message
        self.status_code = status_code
        self.title = title
        super().__init__(message)

    def get_error(self, request: Request) -> dict:
        return {
            "type": f"{request.base_url}openapi.json",
            "title": self.title,
            "status": self.status_code,
            "detail": self.message,
            "instance": str(request.url),
        }


async def base_exception_handler(request: Request, exc: Exception):
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
            )
        case BaseException():
            return JSONResponse(
                status_code=exc.status_code,
                content=exc.get_error(request),
            )
        case _:
            logger.error(str(exec))
            return JSONResponse(
                status_code=500,
                content={
                    "type": "about:blank",
                    "title": "Internal Server Error",
                    "status": 500,
                    "detail": None,
                    "instance": str(request.url),
                },
            )
