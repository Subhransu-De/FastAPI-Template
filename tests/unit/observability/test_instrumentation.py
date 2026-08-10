import asyncio
import subprocess
import sys
from types import SimpleNamespace
from typing import Any, cast

import pytest
from fastapi import FastAPI
from opentelemetry.sdk.trace.export import ConsoleSpanExporter, SimpleSpanProcessor
from sqlalchemy.ext.asyncio import create_async_engine

from app.observability import configuration, instrumentation

pytestmark = pytest.mark.unit


def test_configure_observability_disables_hosted_logfire_export(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[dict[str, object]] = []

    def configure(**kwargs: object) -> None:
        calls.append(kwargs)

    monkeypatch.setattr(configuration, "_configured", False)
    monkeypatch.setattr(configuration.logfire, "configure", configure)

    configuration.configure_observability()

    assert len(calls) == 1
    call = calls[0]
    assert call["service_name"] == configuration.app_settings.app_name
    assert call["send_to_logfire"] is False
    assert call["console"] is False
    assert call["metrics"] is False

    processors = call["additional_span_processors"]
    assert isinstance(processors, list)
    assert len(processors) == 1
    processor = processors[0]
    assert isinstance(processor, SimpleSpanProcessor)
    assert isinstance(processor.span_exporter, ConsoleSpanExporter)


def test_format_span_outputs_one_json_record_per_line() -> None:
    span = SimpleNamespace(
        to_json=lambda *, indent: '{"name":"request"}' if indent is None else ""
    )

    output = configuration._format_span(cast("Any", span))

    assert output == '{"name":"request"}\n'


def test_observability_package_imports_without_order_dependencies() -> None:
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            "from app import observability; print(observability.__name__)",
        ],
        capture_output=True,
        check=True,
        text=True,
    )

    assert result.stdout.strip() == "app.observability"


def test_instrument_sqlalchemy_unwraps_async_engine(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    calls: list[object] = []

    monkeypatch.setattr(instrumentation, "configure_observability", lambda: None)
    monkeypatch.setattr(instrumentation, "_instrumented_sqlalchemy_engines", set())
    monkeypatch.setattr(
        instrumentation.logfire,
        "instrument_sqlalchemy",
        lambda *, engine: calls.append(engine),
    )

    try:
        instrumentation.instrument_sqlalchemy(engine)
        instrumentation.instrument_sqlalchemy(engine)
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

    mapped = instrumentation._request_attributes_mapper(
        cast("Any", request), attributes
    )

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

    monkeypatch.setattr(instrumentation, "configure_observability", lambda: None)
    monkeypatch.setattr(instrumentation, "_instrumented_fastapi_apps", set())
    monkeypatch.setattr(
        instrumentation.logfire,
        "instrument_fastapi",
        lambda app, **kwargs: calls.append({"app": app, **kwargs}),
    )

    instrumentation.instrument_fastapi(app)

    assert instrumentation.EXCLUDED_FASTAPI_PATHS == ["/health"]
    assert calls == [
        {
            "app": app,
            "request_attributes_mapper": instrumentation._request_attributes_mapper,
            "excluded_urls": instrumentation._excluded_url_patterns(),
        }
    ]
