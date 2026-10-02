from http import HTTPStatus

import logfire
from fastapi import Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import Response
from sqlalchemy.exc import OperationalError
from sqlalchemy.exc import TimeoutError as PoolTimeoutError
from starlette.exceptions import HTTPException

from app.exceptions.base import BaseError, ProblemDetails, problem_response
from app.exceptions.exceptions import DatabaseUnavailableError


def _validation_errors(exc: RequestValidationError) -> list[dict[str, object]]:
    return [dict(error) for error in jsonable_encoder(exc.errors())]


def _http_error_title(status_code: int) -> str:
    try:
        return HTTPStatus(status_code).phrase
    except ValueError:
        return "HTTP Error"


def _http_error_detail(exc: HTTPException) -> str:
    return exc.detail if isinstance(exc.detail, str) else str(exc.detail)


def base_exception_handler(request: Request, exc: Exception) -> Response:
    match exc:
        case RequestValidationError():
            return problem_response(
                ProblemDetails(
                    type=f"{request.base_url}openapi.json",
                    title=HTTPStatus.UNPROCESSABLE_CONTENT.phrase,
                    status=HTTPStatus.UNPROCESSABLE_CONTENT,
                    detail=_validation_errors(exc),
                    instance=str(request.url),
                )
            )
        case BaseError():
            return problem_response(exc.problem(request), exc.headers)
        case OperationalError() | PoolTimeoutError():
            logfire.exception(
                "Database unavailable while processing {url}",
                url=str(request.url),
                _exc_info=exc,
            )
            return problem_response(DatabaseUnavailableError().problem(request))
        case HTTPException():
            return problem_response(
                ProblemDetails(
                    title=_http_error_title(exc.status_code),
                    status=exc.status_code,
                    detail=_http_error_detail(exc),
                    instance=str(request.url),
                ),
                exc.headers,
            )
        case _:
            logfire.exception(
                "Unhandled exception while processing {url}",
                url=str(request.url),
                _exc_info=exc,
            )
            return problem_response(
                ProblemDetails(
                    title=HTTPStatus.INTERNAL_SERVER_ERROR.phrase,
                    status=HTTPStatus.INTERNAL_SERVER_ERROR,
                    detail="An unexpected error occurred.",
                    instance=str(request.url),
                )
            )
