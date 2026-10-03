from collections.abc import Callable
from dataclasses import dataclass
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

type ValidationRenderer = Callable[
    [Request, RequestValidationError, HTTPStatus], ProblemDetails
]


def _validation_errors(exc: RequestValidationError) -> list[dict[str, object]]:
    return [dict(error) for error in jsonable_encoder(exc.errors())]


def _http_error_title(status_code: int) -> str:
    try:
        return HTTPStatus(status_code).phrase
    except ValueError:
        return "HTTP Error"


def _http_error_detail(exc: HTTPException) -> str:
    return exc.detail if isinstance(exc.detail, str) else str(exc.detail)


def render_validation_problem(
    request: Request,
    exc: RequestValidationError,
    status: HTTPStatus,
) -> ProblemDetails:
    return ProblemDetails(
        type=f"{request.base_url}openapi.json",
        title=status.phrase,
        status=status,
        detail=_validation_errors(exc),
        instance=str(request.url),
    )


@dataclass(frozen=True, slots=True, kw_only=True)
class ErrorHandling:
    validation_status: HTTPStatus = HTTPStatus.UNPROCESSABLE_CONTENT
    render_validation: ValidationRenderer = render_validation_problem

    def handle(self, request: Request, exc: Exception) -> Response:
        match exc:
            case RequestValidationError():
                return problem_response(
                    self.render_validation(request, exc, self.validation_status)
                )
            case BaseError():
                return exc.response(request)
            case OperationalError() | PoolTimeoutError():
                logfire.exception(
                    "Database unavailable while processing {url}",
                    url=str(request.url),
                    _exc_info=exc,
                )
                return DatabaseUnavailableError().response(request)
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
