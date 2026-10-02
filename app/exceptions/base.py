from collections.abc import Mapping
from http import HTTPStatus

from fastapi import Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict

PROBLEM_JSON_MEDIA_TYPE = "application/problem+json"


class ProblemDetails(BaseModel):
    model_config = ConfigDict(frozen=True)

    type: str = "about:blank"
    title: str
    status: int
    detail: str | list[dict[str, object]]
    instance: str


def problem_response(
    problem: ProblemDetails,
    headers: Mapping[str, str] | None = None,
) -> JSONResponse:
    return JSONResponse(
        status_code=problem.status,
        content=problem.model_dump(mode="json"),
        headers=headers,
        media_type=PROBLEM_JSON_MEDIA_TYPE,
    )


def problem_responses(*statuses: HTTPStatus) -> dict[int | str, dict[str, object]]:
    return {
        status.value: {"model": ProblemDetails, "description": status.phrase}
        for status in statuses
    }


class BaseError(Exception):
    def __init__(
        self,
        message: str,
        status_code: int = HTTPStatus.INTERNAL_SERVER_ERROR,
        title: str = HTTPStatus.INTERNAL_SERVER_ERROR.phrase,
        headers: dict[str, str] | None = None,
    ) -> None:
        self.message = message
        self.status_code = status_code
        self.title = title
        self.headers = headers
        super().__init__(message)

    def problem(self, request: Request) -> ProblemDetails:
        return ProblemDetails(
            type=f"{request.base_url}openapi.json",
            title=self.title,
            status=self.status_code,
            detail=self.message,
            instance=str(request.url),
        )
