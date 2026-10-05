# pyright: reportConstantRedefinition=false

"""Test configuration for mapsprovefiber.

Uses MariaDB (Docker) to mirror production when requested, otherwise
defaults to a lightweight SQLite database for pytest runs.
"""

import os
from typing import Any

from .base import *  # noqa

_BASE_DIR = globals()["BASE_DIR"]
_INSTALLED_APPS = globals()["INSTALLED_APPS"]

# -----------------------------------------------------
# Test configuration
# -----------------------------------------------------
DEBUG = False
TESTING = True
# Disable HTTPS redirect during test runs
SECURE_SSL_REDIRECT = False

# Database
# - Default: on-disk SQLite to reduce external dependencies during pytest.
# - Set TEST_DB_ENGINE=postgis (+ DB_*) to run on PostGIS like the CI does (EV-0025: MariaDB saiu).
DATABASES: dict[str, dict[str, Any]]

test_db_engine = os.getenv("TEST_DB_ENGINE", "").lower()

if test_db_engine in {"postgres", "postgresql", "postgis"}:
    DATABASES = {
        "default": {
            "ENGINE": "django.contrib.gis.db.backends.postgis",
            "NAME": os.getenv("DB_NAME", "app"),
            "USER": os.getenv("DB_USER", "app"),
            "PASSWORD": os.getenv("DB_PASSWORD", "app"),
            "HOST": os.getenv("DB_HOST", "postgres"),
            "PORT": os.getenv("DB_PORT", "5432"),
            "OPTIONS": {
                "connect_timeout": 10,
                "options": "-c search_path=public,postgis",
            },
            "TEST": {
                "NAME": os.getenv("TEST_DB_NAME", ""),
            },
        }
    }
    print("[TEST] Environment loaded - PostGIS backend")
else:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": _BASE_DIR / "test_db.sqlite3",
        }
    }
    print("[TEST] Environment loaded - SQLite backend")

# Faster password hashing to avoid bcrypt/argon2 overhead during tests
PASSWORD_HASHERS = [
    "django.contrib.auth.hashers.MD5PasswordHasher",
]

# Local cache and session storage
CACHES: dict[str, dict[str, Any]] = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        "LOCATION": "test-cache",
    }
}
SESSION_ENGINE = "django.contrib.sessions.backends.cache"

# Capture outbound email in memory (nothing is sent)
EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"

# Quiet logging so pytest output stays clean
LOGGING: dict[str, Any] = {
    "version": 1,
    "disable_existing_loggers": True,
    "handlers": {"null": {"class": "logging.NullHandler"}},
    "root": {"handlers": ["null"], "level": "CRITICAL"},
}

# Disable Prometheus during tests
INSTALLED_APPS = [app for app in _INSTALLED_APPS if app != "django_prometheus"]

# Disable FirstTimeSetupRedirectMiddleware during tests to avoid 302 redirects
MIDDLEWARE = [m for m in MIDDLEWARE if "FirstTimeSetupRedirectMiddleware" not in m]  # noqa: F405

# Keep static and media assets isolated per test run
STATICFILES_STORAGE = "django.contrib.staticfiles.storage.StaticFilesStorage"
MEDIA_ROOT = _BASE_DIR / "test_media"

# Celery executes tasks synchronously during tests to avoid broker dependency
os.environ.setdefault("CELERY_BROKER_URL", "memory://")
os.environ.setdefault("CELERY_RESULT_BACKEND", "cache+memory://")
os.environ.setdefault("CELERY_TASK_ALWAYS_EAGER", "true")
os.environ.setdefault("CELERY_TASK_EAGER_PROPAGATES", "true")

CELERY_BROKER_URL = "memory://"
CELERY_RESULT_BACKEND = "cache+memory://"
CELERY_TASK_ALWAYS_EAGER = True
CELERY_TASK_EAGER_PROPAGATES = True
