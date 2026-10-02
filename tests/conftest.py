import asyncio
import selectors
import sys
from typing import Any

import logfire
import pytest

from app import telemetry
from app.settings import Settings
from tests.support import TEST_APP_NAME, build_settings


def selector_event_loop() -> asyncio.AbstractEventLoop:
    return asyncio.SelectorEventLoop(selectors.SelectSelector())


@pytest.fixture
def anyio_backend() -> str | tuple[str, dict[str, Any]]:
    if sys.platform == "win32":
        return "asyncio", {"loop_factory": selector_event_loop}
    return "asyncio"


@pytest.fixture(scope="session", autouse=True)
def _configure_telemetry_before_any_capture() -> None:
    telemetry.configure_otel(TEST_APP_NAME)
    logfire.configure(send_to_logfire=False, console=False)


@pytest.fixture
def settings() -> Settings:
    return build_settings()
