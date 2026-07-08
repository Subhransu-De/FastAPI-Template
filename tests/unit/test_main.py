import importlib
import runpy
import sys
from unittest.mock import Mock

import pytest

pytestmark = pytest.mark.unit


async def test_lifespan_runs_startup_and_shutdown(monkeypatch):
    module = importlib.import_module("app.main")

    setup_logging = Mock()
    info = Mock()

    monkeypatch.setattr(module.logger, "setup_logging", setup_logging)
    monkeypatch.setattr(module.logger, "info", info)

    async with module.lifespan(module.app):
        setup_logging.assert_called_once_with()
        info.assert_called_once_with(
            f"Starting up {module.app_settings.app_name} on port {module.app_settings.port}"
        )

    info.assert_any_call("Application shutdown")


def test_main_runs_uvicorn(monkeypatch):
    module = importlib.import_module("app.main")
    run = Mock()
    setup_logging = Mock()

    monkeypatch.setattr(module.uvicorn, "run", run)
    monkeypatch.setattr(module.logger, "setup_logging", setup_logging)

    module.main()

    setup_logging.assert_called_once_with()
    run.assert_called_once_with(
        "app.main:app",
        host=module.app_settings.host,
        port=module.app_settings.port,
        reload=module.app_settings.reload,
        log_config=None,
    )


def test_running_module_as_script_calls_main(monkeypatch):
    run = Mock()
    existing_module = sys.modules.pop("app.main", None)

    monkeypatch.setattr("uvicorn.run", run)

    try:
        runpy.run_module("app.main", run_name="__main__")
    finally:
        if existing_module is not None:
            sys.modules["app.main"] = existing_module

    run.assert_called_once()
