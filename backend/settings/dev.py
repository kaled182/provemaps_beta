# pyright: reportConstantRedefinition=false

"""Development configuration for mapsprovefiber.

Inherits from ``settings.base`` and applies development-safe overrides.
"""

import os
from importlib import import_module
from typing import Any, Callable, Dict, TYPE_CHECKING

from .base import *  # noqa

if TYPE_CHECKING:  # pragma: no cover - assists type checkers only
    from .base import (
        BASE_DIR,
        BACKEND_DIR,
        FRONTEND_DIR,
        DATABASE_DIR,
        DATABASES,
        INSTALLED_APPS,
        LOGGING,
        MIDDLEWARE,
        TEMPLATES,
    )

# -----------------------------------------------------
# Core
# -----------------------------------------------------
DEBUG = True  # type: ignore[assignment]

# Development hosts (includes Docker/Compose)
ALLOWED_HOSTS = [  # type: ignore[assignment]
    "localhost",
    "127.0.0.1",
    "0.0.0.0",
    "web",                    # docker-compose service name
    "host.docker.internal",   # allows the Docker host to reach the app
]

# CSRF in development
CSRF_TRUSTED_ORIGINS = [  # type: ignore[assignment]
    "http://localhost:8000",
    "http://127.0.0.1:8000",
    "http://0.0.0.0:8000",
    "http://web:8000",
]

# Email is printed to the console
EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"

# -----------------------------------------------------
# Database (Dev optimizations)
# -----------------------------------------------------
# Short-lived connections for development
DATABASES["default"]["CONN_MAX_AGE"] = 0
DATABASES["default"]["OPTIONS"].update({
    "connect_timeout": 3,
})

# Fallback to SQLite when explicitly requested
if os.getenv("DB_ENGINE") == "sqlite":
    DATABASES["default"] = {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": DATABASE_DIR / "db.sqlite3",
    }

# -----------------------------------------------------
# Logging (Dev-friendly)
# -----------------------------------------------------
LOG_LEVEL = "DEBUG"  # type: ignore[assignment]

# Logging tuned for development
LOGGING["formatters"]["verbose"] = {
    "format": "{levelname} {asctime} {module} {message}",
    "style": "{",
}

LOGGING["root"]["level"] = LOG_LEVEL
LOGGING["loggers"]["django"]["level"] = "INFO"
LOGGING["loggers"]["django.db.backends"] = {
    "level": "INFO",  # Change to DEBUG to inspect SQL queries
    "handlers": ["console"],
    "propagate": False,
}

# -----------------------------------------------------
# Debug Toolbar (auto-configure)
# -----------------------------------------------------
# Disable in Docker unless explicitly enabled
ENABLE_DEBUG_TOOLBAR = os.getenv("ENABLE_DEBUG_TOOLBAR", "True").lower() == "true"

if ENABLE_DEBUG_TOOLBAR:
    try:
        import_module("debug_toolbar")
        INSTALLED_APPS.append("debug_toolbar")
        MIDDLEWARE.insert(
            0,
            "debug_toolbar.middleware.DebugToolbarMiddleware",
        )
        DEBUG_TOOLBAR_CONFIG: Dict[str, Callable[[Any], bool]] = {
            "SHOW_TOOLBAR_CALLBACK": lambda request: True,
        }
        INTERNAL_IPS = ["127.0.0.1", "localhost", "0.0.0.0", "172.16.0.0/12"]
        print("[DEBUG_TOOLBAR] Django Debug Toolbar enabled")
    except ImportError:
        print("[INFO] Django Debug Toolbar not installed")
    except Exception as e:
        print(f"[WARN] Error configuring Debug Toolbar: {e}")
else:
    print("[DEBUG_TOOLBAR] Disabled via ENABLE_DEBUG_TOOLBAR=False")


# -----------------------------------------------------
# Development-specific
# -----------------------------------------------------

# Static files in development (Manifest to hash by content)
STATICFILES_STORAGE = (
    "django.contrib.staticfiles.storage.ManifestStaticFilesStorage"
)

# -----------------------------------------------------
# Vue 3 Dashboard Feature Flags (always enabled in dev)
# -----------------------------------------------------
# Garantimos que o template novo (spa.html) seja usado SEMPRE em desenvolvimento
# evitando regressões involuntárias para o template legado.
USE_VUE_DASHBOARD = True  # type: ignore[assignment]
VUE_DASHBOARD_ROLLOUT_PERCENTAGE = 100  # type: ignore[assignment]

import time as _time  # noqa: E402
import subprocess  # noqa: E402


def _git_sha() -> str:
    """Return the short git SHA for the current commit, or ``nosha``."""
    try:
        sha = subprocess.check_output(
            ["git", "rev-parse", "--short", "HEAD"],
            cwd=BASE_DIR,
        ).decode().strip()
        if sha:
            return sha
    except Exception:
        return "nosha"
    return "nosha"


# sha-timestamp for cache busting and traceability
# Use env var if set (for deployment), otherwise generate on module load
_static_version_override = os.getenv("STATIC_ASSET_VERSION")

# Check for deploy-time override file (created by deploy script)
if not _static_version_override:
    _deploy_env_file = BASE_DIR / ".env.deploy"
    if _deploy_env_file.exists():
        try:
            _deploy_content = _deploy_env_file.read_text().strip()
            if _deploy_content.startswith("STATIC_ASSET_VERSION="):
                _static_version_override = _deploy_content.split("=", 1)[1]
        except Exception:
            pass

if _static_version_override:
    STATIC_ASSET_VERSION = _static_version_override
else:
    STATIC_ASSET_VERSION = (
        f"{_git_sha()}-{_time.strftime('%Y%m%d%H%M%S', _time.gmtime())}"
    )
print(f"[STATIC_VERSION] STATIC_ASSET_VERSION={STATIC_ASSET_VERSION}")

# No-cache middleware for sensitive routes
MIDDLEWARE.append("core.middleware.no_cache_dev.NoCacheDevMiddleware")

# Security relaxations for development
if DEBUG:
    SECURE_SSL_REDIRECT = False  # type: ignore[assignment]
    SESSION_COOKIE_SECURE = False  # type: ignore[assignment]
    CSRF_COOKIE_SECURE = False  # type: ignore[assignment]
    
    # Template debugging
    TEMPLATES[0]["OPTIONS"]["debug"] = True

# -----------------------------------------------------
# Development Tools (Optional)
# -----------------------------------------------------

# Django Extensions (when installed)
try:
    import_module("django_extensions")
    INSTALLED_APPS.append("django_extensions")
    print("[DJANGO_EXTENSIONS] Enabled")
except ImportError:
    pass

# Shell plus configuration
SHELL_PLUS = "ipython"
SHELL_PLUS_PRINT_SQL = True

print(f"[DEV] Development environment loaded - DEBUG={DEBUG}")
