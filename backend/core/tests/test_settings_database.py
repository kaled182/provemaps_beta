"""EV-0025: PostGIS é o único banco; `DB_ENGINE` desconhecido falha no arranque."""

from __future__ import annotations

import runpy

import pytest
from django.core.exceptions import ImproperlyConfigured


def _load_base_settings(monkeypatch, **env):
    for key in ("DB_ENGINE", "DB_PORT"):
        monkeypatch.delenv(key, raising=False)
    for key, value in env.items():
        monkeypatch.setenv(key, value)
    return runpy.run_module("settings.base", run_name="settings.base")


def test_default_engine_is_postgis(monkeypatch):
    ns = _load_base_settings(monkeypatch)
    assert ns["DATABASES"]["default"]["ENGINE"] == "django.contrib.gis.db.backends.postgis"
    assert ns["DATABASES"]["default"]["PORT"] == "5432"


@pytest.mark.parametrize("alias", ["postgres", "postgresql", "PostGIS"])
def test_postgres_aliases_are_accepted(monkeypatch, alias):
    ns = _load_base_settings(monkeypatch, DB_ENGINE=alias)
    assert ns["DATABASES"]["default"]["ENGINE"].endswith(".postgis")


@pytest.mark.parametrize("engine", ["mysql", "mariadb", "sqlite3"])
def test_unsupported_engine_fails_loudly(monkeypatch, engine):
    with pytest.raises(ImproperlyConfigured, match="PostgreSQL"):
        _load_base_settings(monkeypatch, DB_ENGINE=engine)


def test_server_entrypoints_default_to_existing_settings_module():
    """`core.settings` nunca existiu; asgi/wsgi caem em `settings.prod` (fail-safe)."""
    import pathlib

    core = pathlib.Path(__file__).resolve().parents[1]
    for name in ("asgi.py", "wsgi.py"):
        source = (core / name).read_text()
        assert "core.settings" not in source.replace(
            "# EV-0025: `core.settings` nunca existiu.", ""
        )
        assert "settings.prod" in source
