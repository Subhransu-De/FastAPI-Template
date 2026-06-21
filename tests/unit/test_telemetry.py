import asyncio
import subprocess
import sys

import pytest
from sqlalchemy.ext.asyncio import create_async_engine

from app import telemetry

pytestmark = pytest.mark.unit


def test_configure_otel_uses_token_aware_logfire_export(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[dict[str, object]] = []

    def configure(**kwargs: object) -> None:
        calls.append(kwargs)

    monkeypatch.setattr(telemetry, "_configured", False)
    monkeypatch.setattr(telemetry.logfire, "configure", configure)

    telemetry.configure_otel()

    assert calls == [
        {
            "service_name": telemetry.app_settings.app_name,
            "send_to_logfire": "if-token-present",
            "console": False,
        }
    ]


def test_telemetry_imports_when_loaded_before_logger() -> None:
    result = subprocess.run(
        [sys.executable, "-c", "from app import telemetry; print(telemetry.__name__)"],
        capture_output=True,
        check=True,
        text=True,
    )

    assert result.stdout.strip() == "app.telemetry"


def test_instrument_sqlalchemy_unwraps_async_engine(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    calls: list[object] = []

    monkeypatch.setattr(telemetry, "_configured", True)
    monkeypatch.setattr(telemetry, "_instrumented_sqlalchemy_engines", set())
    monkeypatch.setattr(
        telemetry.logfire,
        "instrument_sqlalchemy",
        lambda *, engine: calls.append(engine),
    )

    try:
        telemetry.instrument_sqlalchemy(engine)
        telemetry.instrument_sqlalchemy(engine)
    finally:
        awaitable = engine.dispose()

    assert calls == [engine.sync_engine]
    asyncio.run(awaitable)
