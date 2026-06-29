from collections.abc import Callable
from typing import ParamSpec, TypeVar

P = ParamSpec("P")
R = TypeVar("R")
StepFunction = Callable[P, R]

def given(
    step_text: str,
    **kwargs: object,
) -> Callable[[StepFunction[P, R]], StepFunction[P, R]]: ...
def when(
    step_text: str,
    **kwargs: object,
) -> Callable[[StepFunction[P, R]], StepFunction[P, R]]: ...
def then(
    step_text: str,
    **kwargs: object,
) -> Callable[[StepFunction[P, R]], StepFunction[P, R]]: ...
