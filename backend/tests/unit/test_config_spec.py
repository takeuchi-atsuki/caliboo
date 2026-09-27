from pathlib import Path

import pytest

from caliboo_api.config import get_settings


def test_get_settings_default_path(monkeypatch):
    monkeypatch.delenv("CALIBOO_SQLITE_PATH", raising=False)

    settings = get_settings()

    expected = Path(__file__).resolve().parents[2] / "var" / "caliboo.db"
    assert Path(settings.sqlite_path) == expected


def test_get_settings_env_override(monkeypatch, tmp_path):
    custom_path = str(tmp_path / "custom.db")
    monkeypatch.setenv("CALIBOO_SQLITE_PATH", custom_path)

    settings = get_settings()

    assert settings.sqlite_path == custom_path


def test_get_settings_cookie_secure_default_false(monkeypatch):
    monkeypatch.delenv("CALIBOO_COOKIE_SECURE", raising=False)

    settings = get_settings()

    assert settings.cookie_secure is False


@pytest.mark.parametrize("value", ["1", "true", "True", "TRUE"])
def test_get_settings_cookie_secure_enabled_values(monkeypatch, value):
    monkeypatch.setenv("CALIBOO_COOKIE_SECURE", value)

    assert get_settings().cookie_secure is True


@pytest.mark.parametrize("value", ["0", "false", "", "no"])
def test_get_settings_cookie_secure_disabled_values(monkeypatch, value):
    monkeypatch.setenv("CALIBOO_COOKIE_SECURE", value)

    assert get_settings().cookie_secure is False
