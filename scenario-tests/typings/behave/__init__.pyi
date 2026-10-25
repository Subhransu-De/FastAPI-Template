from collections.abc import Callable

def given[**P, R](
    step_text: str,
    **kwargs: object,
) -> Callable[[Callable[P, R]], Callable[P, R]]: ...
def when[**P, R](
    step_text: str,
    **kwargs: object,
) -> Callable[[Callable[P, R]], Callable[P, R]]: ...
def then[**P, R](
    step_text: str,
    **kwargs: object,
) -> Callable[[Callable[P, R]], Callable[P, R]]: ...
