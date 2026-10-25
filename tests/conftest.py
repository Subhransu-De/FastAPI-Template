import asyncio
import selectors
import sys
from collections.abc import Callable

import pytest

from app import telemetry
from app.settings import Settings
from tests.support import TEST_APP_NAME, build_settings


def selector_event_loop() -> asyncio.AbstractEventLoop:
    return asyncio.SelectorEventLoop(selectors.SelectSelector())


def pytest_addoption(parser: pytest.Parser) -> None:
    parser.addoption(
        "--update-openapi-snapshot",
        action="store_true",
        default=False,
        help="Regenerate tests/contract/openapi.json instead of comparing to it.",
    )


@pytest.fixture
def anyio_backend() -> (
    str | tuple[str, dict[str, Callable[[], asyncio.AbstractEventLoop]]]
):
    if sys.platform == "win32":
        return "asyncio", {"loop_factory": selector_event_loop}
    return "asyncio"


@pytest.fixture(scope="session", autouse=True)
def _configure_telemetry_before_any_capture() -> None:
    telemetry.configure_otel(TEST_APP_NAME)


@pytest.fixture
def settings() -> Settings:
    return build_settings()
