import importlib
import runpy
import sys
from unittest.mock import Mock

import pytest

pytestmark = pytest.mark.unit


async def test_lifespan_runs_startup_and_shutdown(monkeypatch):
    module = importlib.import_module("app.main")

    config = Mock()
    config_cls = Mock(return_value=config)
    upgrade = Mock()
    setup_logging = Mock()
    info = Mock()

    monkeypatch.setattr(module, "Config", config_cls)
    monkeypatch.setattr(module.command, "upgrade", upgrade)
    monkeypatch.setattr(module.logger, "setup_logging", setup_logging)
    monkeypatch.setattr(module.logger, "info", info)

    async with module.lifespan(module.app):
        pass

    config_cls.assert_called_once_with("alembic.ini")
    config.set_main_option.assert_called_once_with("script_location", "alembic")
    upgrade.assert_called_once_with(config, "head")
    setup_logging.assert_called_once_with()
    info.assert_any_call(
        f"Starting up {module.settings.app_name} on port {module.settings.port}"
    )
    info.assert_any_call("Application shutdown")


def test_main_runs_uvicorn(monkeypatch):
    module = importlib.import_module("app.main")
    run = Mock()

    monkeypatch.setattr(module.uvicorn, "run", run)

    module.main()

    run.assert_called_once_with(
        "app.main:app",
        host="0.0.0.0",
        port=module.settings.port,
        reload=True,
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
