import pytest
from fastapi.telemetry import TelemetryConfig

from app.main import create_app
from app.settings import Settings
from app.telemetry import HEALTH_ENDPOINT_PATHS

pytestmark = pytest.mark.unit


def _config(settings: Settings) -> TelemetryConfig:
    return create_app(settings)._telemetry


def test_native_telemetry_never_configures_exporters_from_the_environment(
    settings: Settings,
) -> None:
    config = _config(settings)

    assert config["auto_configure"] is False
    assert config["tracer_provider"] is None
    assert config["meter_provider"] is None
    assert config["logger_provider"] is None


@pytest.mark.parametrize("path", HEALTH_ENDPOINT_PATHS)
def test_native_telemetry_excludes_health_probes(settings: Settings, path: str) -> None:
    exclude = _config(settings)["exclude"]

    assert exclude is not None
    assert exclude({"type": "http", "path": path}) is True
    assert exclude({"type": "http", "path": "/entities/"}) is False
