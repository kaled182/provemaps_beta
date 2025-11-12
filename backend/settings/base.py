"""Base settings for the mapsprovefiber project.

- Environment agnostic; overrides live in ``settings.dev`` and
    ``settings.prod``.
- Keeps safe defaults without requiring Redis to be available.
"""

import os
from pathlib import Path
from typing import Any, Dict

# -----------------------------------------------------
# Paths / core
# -----------------------------------------------------
BASE_DIR = Path(__file__).resolve().parent.parent.parent  # backend/ -> project root
BACKEND_DIR = BASE_DIR / 'backend'
FRONTEND_DIR = BASE_DIR / 'frontend'
DATABASE_DIR = BASE_DIR / 'database'

_secret_key = os.getenv("SECRET_KEY")

if not _secret_key:
    settings_module = os.getenv("DJANGO_SETTINGS_MODULE", "")
    # Allow insecure keys automatically in test and development contexts
    if settings_module.endswith(".test"):
        _secret_key = "test-only-insecure-key"
    elif settings_module.endswith(".dev"):
        _secret_key = "dev-only-insecure-key-for-development"
    elif os.getenv("DEBUG", "False").lower() == "true":
        _secret_key = "dev-only-insecure-key-for-development"
    else:
        raise ValueError("SECRET_KEY must be set in production")

SECRET_KEY = _secret_key or ""

DEBUG = os.getenv("DEBUG", "False").lower() == "true"
ALLOWED_HOSTS = [
    host.strip()
    for host in os.getenv("ALLOWED_HOSTS", "localhost,127.0.0.1").split(",")
    if host.strip()
]

ZABBIX_API_URL = os.getenv("ZABBIX_API_URL", "")
ZABBIX_API_USER = os.getenv("ZABBIX_API_USER", "")
ZABBIX_API_PASSWORD = os.getenv("ZABBIX_API_PASSWORD", "")
ZABBIX_API_KEY = os.getenv("ZABBIX_API_KEY", "")
GOOGLE_MAPS_API_KEY = os.getenv("GOOGLE_MAPS_API_KEY", "")
ENABLE_DIAGNOSTIC_ENDPOINTS = (
    os.getenv("ENABLE_DIAGNOSTIC_ENDPOINTS", "False").lower() == "true"
)
SERVICE_RESTART_COMMANDS = os.getenv(
    "SERVICE_RESTART_COMMANDS",
    "",
)

fernet_keys = [
    key.strip()
    for key in os.getenv("FERNET_KEYS", "").split(",")
    if key.strip()
]
if not fernet_keys:
    single_fernet = os.getenv("FERNET_KEY")
    if single_fernet:
        fernet_keys = [single_fernet]
if not fernet_keys:
    fernet_keys = [SECRET_KEY]

FERNET_KEYS = fernet_keys

# Security defaults
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = "DENY"
CSRF_TRUSTED_ORIGINS = [
    origin.strip()
    for origin in os.getenv("CSRF_TRUSTED_ORIGINS", "").split(",")
    if origin.strip()
]

# Extra security toggles when DEBUG is disabled
if not DEBUG:
    SECURE_SSL_REDIRECT = (
        os.getenv("SECURE_SSL_REDIRECT", "True").lower() == "true"
    )
    SECURE_HSTS_SECONDS = int(
        os.getenv("SECURE_HSTS_SECONDS", "31536000")
    )  # 1 year
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_REFERRER_POLICY = os.getenv(
        "SECURE_REFERRER_POLICY", "strict-origin"
    )
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

# Content Security Policy (basic; override via env vars)
# Allow trusted CDNs for Chart.js, Tailwind CSS, and Google Maps API
CSP_DEFAULT_SRC = os.getenv("CSP_DEFAULT_SRC", "'self'").split()
CSP_SCRIPT_SRC = os.getenv(
    "CSP_SCRIPT_SRC",
    "'self' 'unsafe-inline' 'unsafe-eval' "
    "https://cdn.jsdelivr.net "
    "https://cdn.tailwindcss.com "
    "https://maps.googleapis.com",
).split()
CSP_STYLE_SRC = os.getenv(
    "CSP_STYLE_SRC",
    "'self' 'unsafe-inline' "
    "https://cdn.tailwindcss.com "
    "https://fonts.googleapis.com",
).split()
CSP_IMG_SRC = os.getenv(
    "CSP_IMG_SRC",
    "'self' data: "
    "https://maps.googleapis.com "
    "https://maps.gstatic.com "
    "https://*.googleapis.com "
    "https://*.gstatic.com",
).split()
CSP_FONT_SRC = os.getenv(
    "CSP_FONT_SRC",
    "'self' data: https://fonts.gstatic.com",
).split()
CSP_CONNECT_SRC = os.getenv(
    "CSP_CONNECT_SRC",
    "'self' "
    "https://maps.googleapis.com "
    "https://cdn.jsdelivr.net "
    "https://maps.gstatic.com",
).split()
CSP_FRAME_ANCESTORS = os.getenv("CSP_FRAME_ANCESTORS", "'none'").split()
CONTENT_SECURITY_POLICY = {
    "default-src": CSP_DEFAULT_SRC,
    "script-src": CSP_SCRIPT_SRC,
    "style-src": CSP_STYLE_SRC,
    "img-src": CSP_IMG_SRC,
    "font-src": CSP_FONT_SRC,
    "connect-src": CSP_CONNECT_SRC,
    "frame-ancestors": CSP_FRAME_ANCESTORS,
}

# -----------------------------------------------------
# Apps
# -----------------------------------------------------
INSTALLED_APPS = [
    # Django core
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",

    # Geospatial support (Phase 10: PostGIS migration preparation)
    # Enables spatial fields and queries for PostgreSQL + PostGIS
    # NOTE: Works with MySQL but spatial features require PostGIS
    "django.contrib.gis",

    # Observability
    "django_prometheus",

    # Realtime / WebSockets
    "channels",

    # REST API
    "rest_framework",

    # Project apps
    "core.apps.CoreConfig",
    "maps_view",
    "service_accounts.apps.ServiceAccountsConfig",
    # Network inventory (models and routes consolidated in inventory)
    "inventory",
    "setup_app",
    # Modular apps (Phase 0 scaffolding)
    "monitoring",
    "gpon",
    "dwdm",
]

MIDDLEWARE = [
    "django_prometheus.middleware.PrometheusBeforeMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "core.middleware.request_id.RequestIDMiddleware",
    "core.middleware.first_time_setup.FirstTimeSetupRedirectMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    # Adds basic CSP + security headers (configured via env)
    "core.middleware.security_headers.SecurityHeadersMiddleware",
    "django_prometheus.middleware.PrometheusAfterMiddleware",
]

ROOT_URLCONF = "core.urls"
WSGI_APPLICATION = "core.wsgi.application"
ASGI_APPLICATION = "core.asgi.application"

# -----------------------------------------------------
# Database (MySQL/MariaDB with fallbacks) - optimized
# Phase 10: Support for PostgreSQL + PostGIS via DB_ENGINE env var
# -----------------------------------------------------
DB_ENGINE = os.getenv("DB_ENGINE", "mysql").lower()

# MySQL/MariaDB configuration (default, current production)
DB_OPTIONS: Dict[str, Any] = {}

if DB_ENGINE == "mysql":
    DB_OPTIONS = {
        "charset": "utf8mb4",
        "init_command": "SET sql_mode='STRICT_ALL_TABLES'",
        "connect_timeout": 10,
    }
    
    # Optional pool settings when supported by the driver
    if os.getenv("DB_USE_CONNECTION_POOL", "false").lower() == "true":
        DB_OPTIONS.update(
            {
                "pool_size": int(os.getenv("DB_POOL_SIZE", "10")),
                "max_overflow": int(os.getenv("DB_MAX_OVERFLOW", "20")),
                "pool_pre_ping": True,
                "pool_recycle": 300,
            }
        )
elif DB_ENGINE in ("postgres", "postgresql", "postgis"):
    # PostgreSQL + PostGIS configuration (Phase 10)
    DB_OPTIONS = {
        "connect_timeout": 10,
        "options": "-c search_path=public,postgis",
    }

# Database engine selection
if DB_ENGINE in ("postgres", "postgresql", "postgis"):
    DB_BACKEND = "django.contrib.gis.db.backends.postgis"
    DEFAULT_PORT = "5432"
else:
    DB_BACKEND = "django.db.backends.mysql"
    DEFAULT_PORT = "3306"

DATABASES: Dict[str, Dict[str, Any]] = {
    "default": {
        "ENGINE": DB_BACKEND,
        "NAME": os.getenv("DB_NAME", "app"),
        "USER": os.getenv("DB_USER", "app"),
        "PASSWORD": os.getenv("DB_PASSWORD", "app"),
        "HOST": os.getenv("DB_HOST", "127.0.0.1"),
        "PORT": os.getenv("DB_PORT", DEFAULT_PORT),
        "OPTIONS": DB_OPTIONS,
        "CONN_MAX_AGE": int(os.getenv("DB_CONN_MAX_AGE", "0")),
        "ATOMIC_REQUESTS": (
            os.getenv("DB_ATOMIC_REQUESTS", "false").lower() == "true"
        ),
    }
}

# -----------------------------------------------------
# Cache (Redis when available; otherwise resilient fallbacks)
# -----------------------------------------------------
REDIS_URL = os.getenv("REDIS_URL", "").strip()


def get_cache_config() -> Dict[str, Dict[str, Any]]:
    """Return cache settings based on Redis availability."""
    if REDIS_URL:
        return {
            "default": {
                "BACKEND": "django_redis.cache.RedisCache",
                "LOCATION": REDIS_URL,
                "OPTIONS": {
                    "CLIENT_CLASS": "django_redis.client.DefaultClient",
                    "COMPRESSOR": (
                        "django_redis.compressors.zlib.ZlibCompressor"
                    ),
                    "SOCKET_CONNECT_TIMEOUT": 5,
                    "SOCKET_TIMEOUT": 5,
                    "RETRY_ON_TIMEOUT": True,
                    "MAX_CONNECTIONS": int(
                        os.getenv("REDIS_MAX_CONNECTIONS", "100")
                    ),
                },
                "KEY_PREFIX": "mapsprovefiber",
                "VERSION": 1,
            }
        }
    # Production without Redis uses file-based cache; dev falls back to locmem
    if not DEBUG:
        return {
            "default": {
                "BACKEND": (
                    "django.core.cache.backends.filebased.FileBasedCache"
                ),
                "LOCATION": "/tmp/django_cache",
                "TIMEOUT": 300,
                "OPTIONS": {"MAX_ENTRIES": 1000},
            }
        }

    return {
        "default": {
            "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
            "LOCATION": "mapsprovefiber-local",
        }
    }


CACHES = get_cache_config()

# Sessions
if REDIS_URL:
    session_engine = "django.contrib.sessions.backends.cache"
    SESSION_CACHE_ALIAS = "default"
    SESSION_COOKIE_AGE = int(
        os.getenv("SESSION_COOKIE_AGE", "1209600")
    )  # 2 weeks
else:
    session_engine = "django.contrib.sessions.backends.db"

SESSION_ENGINE = session_engine

# -----------------------------------------------------
# ASGI / Channels (WebSockets)
# -----------------------------------------------------
CHANNEL_LAYER_URL = os.getenv(
    "CHANNEL_LAYER_URL", os.getenv("REDIS_URL", "")
).strip()
CHANNEL_PREFIX = os.getenv("CHANNEL_REDIS_PREFIX", "mapsprovefiber")

if CHANNEL_LAYER_URL.startswith(("redis://", "rediss://")):
    channel_layers: Dict[str, Dict[str, Any]] = {
        "default": {
            "BACKEND": "channels_redis.core.RedisChannelLayer",
            "CONFIG": {
                "hosts": [CHANNEL_LAYER_URL],
                "prefix": CHANNEL_PREFIX,
            },
        }
    }
else:
    channel_layers = {
        "default": {
            "BACKEND": "channels.layers.InMemoryChannelLayer",
        }
    }

CHANNEL_LAYERS = channel_layers

# -----------------------------------------------------
# Internationalization / timezone
# -----------------------------------------------------
LANGUAGE_CODE = os.getenv("LANGUAGE_CODE", "pt-br")
TIME_ZONE = os.getenv("TIME_ZONE", "America/Belem")
USE_I18N = True
USE_TZ = True

# -----------------------------------------------------
# Static and media files
# -----------------------------------------------------
STATIC_URL = "/static/"
STATIC_ROOT = BACKEND_DIR / "staticfiles"
MEDIA_URL = "/media/"
MEDIA_ROOT = BACKEND_DIR / "media"
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# Cache-busting version (overridden via STATIC_ASSET_VERSION in env)
STATIC_ASSET_VERSION = os.getenv("STATIC_ASSET_VERSION", "20251026.1")

# -----------------------------------------------------
# Templates (cache enabled in production)
# -----------------------------------------------------
TEMPLATES: list[Dict[str, Any]] = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BACKEND_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "setup_app.context_processors.static_version",
            ],
        },
    },
]

if not DEBUG:
    # Enable template caching in production (fine-tuned in settings/prod.py)
    # Keep APP_DIRS=True here and delegate loaders to the production file.
    pass

# -----------------------------------------------------
# Health check configuration
# -----------------------------------------------------
HEALTHCHECK_CONFIG: Dict[str, Any] = {
    "DISK_THRESHOLD_GB": float(
        os.getenv("HEALTHCHECK_DISK_THRESHOLD_GB", "1.0")
    ),
    "DB_TIMEOUT": int(os.getenv("HEALTHCHECK_DB_TIMEOUT", "5")),
    "ENABLE_STORAGE_CHECK": (
        os.getenv("HEALTHCHECK_STORAGE", "true").lower() == "true"
    ),
    "ENABLE_SYSTEM_METRICS": (
        os.getenv("HEALTHCHECK_SYSTEM_METRICS", "false").lower() == "true"
    ),
    "DEBUG": os.getenv("HEALTHCHECK_DEBUG", "false").lower() == "true",
}

# -----------------------------------------------------
# Logging (optional rotation support)
# -----------------------------------------------------
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
LOG_FORMAT = os.getenv("LOG_FORMAT", "verbose")  # "simple" or "verbose"

FORMATTERS = {
    "verbose": {
        "format": (
            "{levelname} {asctime} {module} {process:d} {thread:d} {message}"
        ),
        "style": "{",
    },
    "simple": {
        "format": "{levelname} {asctime} {message}",
        "style": "{",
    },
}

HANDLERS: Dict[str, Dict[str, Any]] = {
    "console": {
        "class": "logging.StreamHandler",
        "formatter": LOG_FORMAT,
    },
}

# Optional file handler (production only when enabled)
if not DEBUG and os.getenv("ENABLE_FILE_LOGGING", "false").lower() == "true":
    HANDLERS["file"] = {
        "class": "logging.handlers.RotatingFileHandler",
        "filename": os.getenv("LOG_FILE", "/var/log/django/app.log"),
        "maxBytes": int(os.getenv("LOG_MAX_BYTES", "10485760")),  # 10 MB
        "backupCount": int(os.getenv("LOG_BACKUP_COUNT", "5")),
        "formatter": LOG_FORMAT,
    }

LOGGING: Dict[str, Any] = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": FORMATTERS,
    "handlers": HANDLERS,
    "root": {
        "handlers": list(HANDLERS.keys()),
        "level": LOG_LEVEL,
    },
    "loggers": {
        "django": {
            "handlers": list(HANDLERS.keys()),
            "level": os.getenv("DJANGO_LOG_LEVEL", "INFO"),
            "propagate": False,
        },
        "django.db.backends": {
            "handlers": list(HANDLERS.keys()),
            "level": os.getenv("DB_LOG_LEVEL", "INFO"),
            "propagate": False,
        },
    },
}

# Optional detailed query logging
if os.getenv("ENABLE_DB_QUERY_LOG", "false").lower() == "true":
    LOGGING["loggers"]["django.db.backends"] = {
        "level": "DEBUG",
        "handlers": ["console"],
        "propagate": False,
    }

# -----------------------------------------------------
# Monitoring (Sentry - optional)
# -----------------------------------------------------
SENTRY_DSN = os.getenv("SENTRY_DSN", "")
if SENTRY_DSN:
    try:
        import sentry_sdk  # type: ignore
        import sentry_sdk.integrations.celery as sentry_celery  # type: ignore
        import sentry_sdk.integrations.django as sentry_django  # type: ignore

        django_integration_cls = getattr(sentry_django, "DjangoIntegration")
        celery_integration_cls = getattr(sentry_celery, "CeleryIntegration")

        sentry_sdk.init(  # type: ignore[no-untyped-call]
            dsn=SENTRY_DSN,
            integrations=[
                django_integration_cls(),
                celery_integration_cls(),
            ],
            traces_sample_rate=float(
                os.getenv("SENTRY_TRACES_SAMPLE_RATE", "0.1")
            ),
            profiles_sample_rate=float(
                os.getenv("SENTRY_PROFILES_SAMPLE_RATE", "0.0")
            ),
            environment=os.getenv("SENTRY_ENVIRONMENT", "development"),
            debug=DEBUG,
        )
    except ImportError:
        # Sentry is optional; skip initialization if it's not installed
        pass

# ===========================
# Django REST Framework
# ===========================

REST_FRAMEWORK: dict[str, object] = {
    "DEFAULT_RENDERER_CLASSES": [
        "rest_framework.renderers.JSONRenderer",
    ],
    "DEFAULT_PARSER_CLASSES": [
        "rest_framework.parsers.JSONParser",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",
    ],
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework.authentication.SessionAuthentication",
    ],
    "DEFAULT_PAGINATION_CLASS": (
        "rest_framework.pagination.PageNumberPagination"
    ),
    "PAGE_SIZE": 100,
}
