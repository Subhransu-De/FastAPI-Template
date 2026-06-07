import pytest

from app import telemetry

pytestmark = pytest.mark.unit


def test_configure_otel_disables_logfire_export(
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
            "send_to_logfire": False,
            "console": False,
        }
    ]
