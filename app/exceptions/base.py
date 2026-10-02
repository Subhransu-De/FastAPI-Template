from collections.abc import Mapping
from http import HTTPStatus
from typing import ClassVar

from fastapi import Request
from fastapi.responses import JSONResponse, Response
from pydantic import BaseModel, ConfigDict
from pydantic.config import JsonDict

PROBLEM_JSON_MEDIA_TYPE = "application/problem+json"


def _omit_implied_additional_properties(schema: JsonDict) -> None:
    schema.pop("additionalProperties", None)


class ProblemDetails(BaseModel):
    model_config = ConfigDict(
        frozen=True,
        extra="allow",
        json_schema_extra=_omit_implied_additional_properties,
    )

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


def empty_responses(*statuses: HTTPStatus) -> dict[int | str, dict[str, object]]:
    return {status.value: {"description": status.phrase} for status in statuses}


class BaseError(Exception):
    has_body: ClassVar[bool] = True

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

    def response(self, request: Request) -> Response:
        if not self.has_body:
            return Response(status_code=self.status_code, headers=self.headers)
        return problem_response(self.problem(request), self.headers)
