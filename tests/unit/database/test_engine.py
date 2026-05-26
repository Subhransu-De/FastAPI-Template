from unittest.mock import MagicMock, patch

import pytest

import app.database.engine as engine_module

pytestmark = pytest.mark.unit


def test_get_engine_creates_engine_with_settings(monkeypatch):
    monkeypatch.setattr(engine_module, "_engine", None)
    mock_engine = MagicMock()

    with patch(
        "app.database.engine.create_async_engine", return_value=mock_engine
    ) as mock_create:
        result = engine_module.get_engine()

    assert result is mock_engine
    mock_create.assert_called_once()


def test_get_engine_returns_same_instance_on_second_call(monkeypatch):
    monkeypatch.setattr(engine_module, "_engine", None)
    mock_engine = MagicMock()

    with patch(
        "app.database.engine.create_async_engine", return_value=mock_engine
    ) as mock_create:
        first = engine_module.get_engine()
        second = engine_module.get_engine()

    assert first is second
    mock_create.assert_called_once()
