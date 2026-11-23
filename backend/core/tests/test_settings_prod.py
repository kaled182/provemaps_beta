"""EV-0037 — o perfil de produção arranca e mantém o comportamento que a produção
tinha em settings.dev (e-mail do runtime.env, dashboard Vue, cookie CSRF legível,
cache do base), além do endurecimento."""

import importlib
import os
import sys
from unittest.mock import patch

import pytest

PROD_ENV = {
    "SECRET_KEY": "x" * 50,
    "ALLOWED_HOSTS": "provemaps.example.org,localhost",
    "CSRF_TRUSTED_ORIGINS": "https://provemaps.example.org",
    "SENTRY_DSN": "",
}


def _load_prod(extra=None):
    env = {**PROD_ENV, **(extra or {})}
    with patch.dict(os.environ, env):
        for mod in ("settings.prod", "settings.base", "settings.runtime_env"):
            sys.modules.pop(mod, None)
        return importlib.import_module("settings.prod")


def test_prod_profile_matches_current_behaviour():
    prod = _load_prod()
    assert prod.DEBUG is False
    assert prod.ALLOWED_HOSTS == ["provemaps.example.org", "localhost"]
    assert prod.CSRF_COOKIE_HTTPONLY is False  # o frontend lê o cookie csrftoken
    assert prod.USE_VUE_DASHBOARD is True
    assert prod.VUE_DASHBOARD_ROLLOUT_PERCENTAGE == 100
    assert prod.DATABASES["default"]["CONN_MAX_AGE"] == 0
    # cache do base, não a configuração com HiredisParser (não existe no redis-py 7)
    assert "PARSER_CLASS" not in str(prod.CACHES)
    # loaders explícitos exigem APP_DIRS=False
    assert prod.TEMPLATES[0]["APP_DIRS"] is False
    assert prod.SECURE_SSL_REDIRECT is True
    assert prod.SESSION_COOKIE_SECURE is True


def test_prod_refuses_without_allowed_hosts():
    with pytest.raises(ValueError, match="ALLOWED_HOSTS"):
        _load_prod({"ALLOWED_HOSTS": ""})


def test_runtime_email_env_loaded_without_overriding(tmp_path):
    from settings.runtime_env import load_runtime_email_env

    (tmp_path / "runtime.env").write_text(
        'EMAIL_HOST="smtp.exemplo"\nEMAIL_PORT=2525\nDB_PASSWORD=nao-carregar\n', encoding="utf-8"
    )
    with patch.dict(os.environ, {"EMAIL_PORT": "587"}, clear=False):
        os.environ.pop("EMAIL_HOST", None)
        os.environ.pop("ENV_FILE_PATH", None)
        load_runtime_email_env(tmp_path)
        assert os.environ["EMAIL_HOST"] == "smtp.exemplo"
        assert os.environ["EMAIL_PORT"] == "587"  # o ambiente ganha
        assert "nao-carregar" not in os.environ.values()
        os.environ.pop("EMAIL_HOST", None)
