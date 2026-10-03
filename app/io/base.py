from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel


class CamelModel(BaseModel):
    model_config = ConfigDict(
        alias_generator=to_camel,
        validate_by_alias=True,
        validate_by_name=False,
        serialize_by_alias=True,
        extra="forbid",
    )


class CamelResponse(CamelModel):
    model_config = ConfigDict(
        from_attributes=True,
        validate_by_name=True,
        extra="ignore",
    )
