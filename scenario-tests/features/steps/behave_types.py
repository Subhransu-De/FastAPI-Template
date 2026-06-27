from collections.abc import Callable
from typing import ParamSpec, Protocol, TypeVar

# Behave 1.3.3 ships without PEP 561 metadata (`py.typed`) or `.pyi` stubs.
# Upstream tracks this typing gap at https://github.com/behave/behave/issues/1168,
# so we type only the step decorator shape used by these scenario tests.
P = ParamSpec("P")
R = TypeVar("R")
StepFunction = Callable[P, R]


class StepDecorator(Protocol):
    def __call__(
        self,
        step_text: str,
        **kwargs: object,
    ) -> Callable[[StepFunction[P, R]], StepFunction[P, R]]: ...
