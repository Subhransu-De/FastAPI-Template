import asyncio
import subprocess
import sys
from types import SimpleNamespace
from typing import Any, cast

import pytest
from fastapi import FastAPI
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


def test_request_attributes_mapper_drops_endpoint_values() -> None:
    request = SimpleNamespace(
        headers={},
        client=SimpleNamespace(host="127.0.0.1"),
        state=SimpleNamespace(auth_claims={"client_id": "api-client"}),
    )
    attributes = {
        "values": {"payload": {"description": "private"}},
        "errors": [{"loc": ["body", "name"], "msg": "missing"}],
    }

    mapped = telemetry._request_attributes_mapper(cast("Any", request), attributes)

    assert mapped == {
        "errors": [{"loc": ["body", "name"], "msg": "missing"}],
        "client.ip": "127.0.0.1",
        "oidc.client_id": "api-client",
    }
    assert "values" in attributes
    assert "values" not in mapped


def test_instrument_fastapi_excludes_health_endpoint(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    app = FastAPI()
    calls: list[dict[str, object]] = []

    monkeypatch.setattr(telemetry, "_configured", True)
    monkeypatch.setattr(telemetry, "_instrumented_fastapi_apps", set())
    monkeypatch.setattr(
        telemetry.logfire,
        "instrument_fastapi",
        lambda app, **kwargs: calls.append({"app": app, **kwargs}),
    )

    telemetry.instrument_fastapi(app)

    assert calls == [
        {
            "app": app,
            "request_attributes_mapper": telemetry._request_attributes_mapper,
            "excluded_urls": r".*/health/db(?:\?.*)?$",
        }
    ]
