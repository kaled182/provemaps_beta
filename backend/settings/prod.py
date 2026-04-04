# pyright: reportConstantRedefinition=false

"""Production configuration for mapsprovefiber.

Extends ``settings.base`` with HTTPS/HSTS hardening, reverse-proxy support,
and production-grade logging tweaks.
"""

import os
from typing import Any, Dict

import structlog

from .base import *  # noqa

# -----------------------------------------------------
# Initial validation
# -----------------------------------------------------

# Validate SECRET_KEY for production
_secret_key = globals()["SECRET_KEY"]
if _secret_key == "dev-only-insecure-key-for-development":
    raise ValueError(
        (
            "SECRET_KEY cannot use the development default when running in "
            "production. Set the SECRET_KEY environment variable."
        )
    )

# -----------------------------------------------------
# Core
# -----------------------------------------------------
DEBUG = False

# Hosts required for production
ALLOWED_HOSTS = [
    host.strip()
    for host in os.getenv("ALLOWED_HOSTS", "").split(",")
    if host.strip()
]

if not ALLOWED_HOSTS:
    raise ValueError(
        (
            "On production deployments set ALLOWED_HOSTS (e.g. "
            "ALLOWED_HOSTS=app.example.com,api.example.com)"
        )
    )

# CSRF origins
CSRF_TRUSTED_ORIGINS = [
    origin.strip()
    for origin in os.getenv("CSRF_TRUSTED_ORIGINS", "").split(",")
    if origin.strip()
]

# -----------------------------------------------------
# Security (HTTPS / headers)
# -----------------------------------------------------
SECURE_SSL_REDIRECT = (
    os.getenv("SECURE_SSL_REDIRECT", "true").lower() == "true"
)

# Proxy configuration
USE_X_FORWARDED_HOST = (
    os.getenv("USE_X_FORWARDED_HOST", "true").lower() == "true"
)
if USE_X_FORWARDED_HOST:
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

# Cookie security
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SESSION_COOKIE_HTTPONLY = True
CSRF_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = os.getenv("SESSION_COOKIE_SAMESITE", "Lax")

# HSTS
SECURE_HSTS_SECONDS = int(
    os.getenv("SECURE_HSTS_SECONDS", str(60 * 60 * 24 * 365))
)  # 1 year
SECURE_HSTS_INCLUDE_SUBDOMAINS = (
    os.getenv("SECURE_HSTS_INCLUDE_SUBDOMAINS", "true").lower() == "true"
)
SECURE_HSTS_PRELOAD = (
    os.getenv("SECURE_HSTS_PRELOAD", "true").lower() == "true"
)

# Security headers
SECURE_REFERRER_POLICY = os.getenv(
    "SECURE_REFERRER_POLICY",
    "strict-origin-when-cross-origin",
)
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_BROWSER_XSS_FILTER = True
X_FRAME_OPTIONS = "DENY"

# -----------------------------------------------------
# Performance & optimization
# -----------------------------------------------------

# Database
_db_default = globals()["DATABASES"]["default"]
_db_default["CONN_MAX_AGE"] = int(os.getenv("DB_CONN_MAX_AGE", "300"))
_db_default["OPTIONS"].update(
    {
        "connect_timeout": 10,
        "read_timeout": 30,
        "write_timeout": 30,
    }
)

# Template caching
_template_options = globals()["TEMPLATES"][0]["OPTIONS"]
_template_options["loaders"] = [
    (
        "django.template.loaders.cached.Loader",
        [
            "django.template.loaders.filesystem.Loader",
            "django.template.loaders.app_directories.Loader",
        ],
    )
]

# Static files
STATICFILES_STORAGE = (
    "django.contrib.staticfiles.storage.ManifestStaticFilesStorage"
)

# File upload limits
DATA_UPLOAD_MAX_MEMORY_SIZE = int(
    os.getenv("DATA_UPLOAD_MAX_MEMORY_SIZE", "10485760")
)  # 10 MB
FILE_UPLOAD_MAX_MEMORY_SIZE = int(
    os.getenv("FILE_UPLOAD_MAX_MEMORY_SIZE", "10485760")
)

# -----------------------------------------------------
# Redis high-availability configuration
# -----------------------------------------------------
# Option A: Managed Service (AWS ElastiCache, Google Memorystore, Azure Cache)
# Set REDIS_URL to managed service endpoint
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

# Option B: Self-Managed Redis Sentinel
# Uncomment below and set REDIS_USE_SENTINEL=true
REDIS_USE_SENTINEL = os.getenv("REDIS_USE_SENTINEL", "false").lower() == "true"

CACHES: Dict[str, Dict[str, Any]]
CHANNEL_LAYERS: Dict[str, Dict[str, Any]]
CELERY_BROKER_TRANSPORT_OPTIONS: Dict[str, Any] = {}

if REDIS_USE_SENTINEL:
    # Parse sentinel hosts from env: "host1:port1,host2:port2,host3:port3"
    sentinel_hosts_str = os.getenv("REDIS_SENTINELS", "localhost:26379")
    REDIS_SENTINELS = [
        (h.split(":")[0], int(h.split(":")[1]))
        for h in sentinel_hosts_str.split(",")
        if ":" in h
    ]
    REDIS_MASTER_NAME = os.getenv("REDIS_MASTER_NAME", "mymaster")
    REDIS_PASSWORD = os.getenv("REDIS_PASSWORD", None)
    
    # Cache with Sentinel
    CACHES = {
        "default": {
            "BACKEND": "django_redis.cache.RedisCache",
            "LOCATION": f"redis://{REDIS_MASTER_NAME}/0",
            "OPTIONS": {
                "CLIENT_CLASS": "django_redis.client.SentinelClient",
                "SENTINELS": REDIS_SENTINELS,
                "SENTINEL_KWARGS": {
                    "password": REDIS_PASSWORD,
                } if REDIS_PASSWORD else {},
                "PASSWORD": REDIS_PASSWORD,
                "CONNECTION_POOL_KWARGS": {
                    "max_connections": 50,
                    "retry_on_timeout": True,
                },
                "SOCKET_CONNECT_TIMEOUT": 5,
                "SOCKET_TIMEOUT": 5,
            }
        }
    }
    
    # Celery with Sentinel
    sentinel_urls = ";".join(
        [f"sentinel://{h}:{p}" for h, p in REDIS_SENTINELS]
    )
    CELERY_BROKER_URL = sentinel_urls
    CELERY_BROKER_TRANSPORT_OPTIONS = {
        "master_name": REDIS_MASTER_NAME,
        "sentinel_kwargs": (
            {"password": REDIS_PASSWORD} if REDIS_PASSWORD else {}
        ),
    }
    CELERY_RESULT_BACKEND = sentinel_urls
    
    # Channels with Sentinel
    CHANNEL_LAYERS = {
        "default": {
            "BACKEND": "channels_redis.core.RedisChannelLayer",
            "CONFIG": {
                "hosts": REDIS_SENTINELS,
                "master_name": REDIS_MASTER_NAME,
                "sentinel_kwargs": (
                    {"password": REDIS_PASSWORD} if REDIS_PASSWORD else {}
                ),
                "password": REDIS_PASSWORD,
                "capacity": 1500,
                "expiry": 10,
            },
        },
    }
else:
    # Standard Redis configuration (Managed Service or single instance)
    CACHES = {
        "default": {
            "BACKEND": "django_redis.cache.RedisCache",
            "LOCATION": REDIS_URL,
            "OPTIONS": {
                "CLIENT_CLASS": "django_redis.client.DefaultClient",
                "SOCKET_CONNECT_TIMEOUT": 5,
                "SOCKET_TIMEOUT": 5,
                "CONNECTION_POOL_KWARGS": {
                    "max_connections": 50,
                    "retry_on_timeout": True
                },
                "PARSER_CLASS": "redis.connection.HiredisParser",
            }
        }
    }
    
    # Celery
    CELERY_BROKER_URL = REDIS_URL
    CELERY_RESULT_BACKEND = REDIS_URL
    CELERY_BROKER_CONNECTION_RETRY_ON_STARTUP = True
    
    # Channels
    CHANNEL_LAYERS = {
        "default": {
            "BACKEND": "channels_redis.core.RedisChannelLayer",
            "CONFIG": {
                "hosts": [REDIS_URL],
                "capacity": 1500,
                "expiry": 10,
            },
        },
    }

# -----------------------------------------------------
# Email
# -----------------------------------------------------
EMAIL_BACKEND = os.getenv(
    "EMAIL_BACKEND",
    "django.core.mail.backends.smtp.EmailBackend",
)
EMAIL_HOST = os.getenv("EMAIL_HOST", "")
EMAIL_PORT = int(os.getenv("EMAIL_PORT", "587")) if EMAIL_HOST else None
EMAIL_HOST_USER = os.getenv("EMAIL_HOST_USER", "")
EMAIL_HOST_PASSWORD = os.getenv("EMAIL_HOST_PASSWORD", "")

if EMAIL_HOST:
    EMAIL_USE_TLS = os.getenv("EMAIL_USE_TLS", "true").lower() == "true"
    EMAIL_USE_SSL = os.getenv("EMAIL_USE_SSL", "false").lower() == "true"
else:
    EMAIL_USE_TLS = None
    EMAIL_USE_SSL = None
DEFAULT_FROM_EMAIL = os.getenv("DEFAULT_FROM_EMAIL", "no-reply@localhost")
SERVER_EMAIL = DEFAULT_FROM_EMAIL  # Used for error reports

# -----------------------------------------------------
# Logging (production-ready with structlog)
# -----------------------------------------------------
try:
    import pythonjsonlogger  # noqa: F401
    _json_logger_available = True
except ImportError:
    _json_logger_available = False

LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
DJANGO_LOG_LEVEL = os.getenv("DJANGO_LOG_LEVEL", "WARNING")

# Standard Django logging configuration
LOGGING: Dict[str, Any] = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "json": {
            "()": "pythonjsonlogger.jsonlogger.JsonFormatter",
            "format": (
                "%(levelname)s %(asctime)s %(name)s %(module)s "
                "%(process)d %(thread)d %(message)s"
            ),
        } if _json_logger_available else {
            "format": (
                '{"level":"%(levelname)s","time":"%(asctime)s",'
                '"name":"%(name)s","message":"%(message)s"}'
            ),
            "datefmt": "%Y-%m-%dT%H:%M:%S",
        },
        "simple": {
            "format": "[%(levelname)s] %(asctime)s %(name)s: %(message)s",
            "datefmt": "%Y-%m-%d %H:%M:%S",
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": (
                "json" if os.getenv("LOG_FORMAT") == "json" else "simple"
            ),
        },
    },
    "root": {
        "handlers": ["console"],
        "level": LOG_LEVEL,
    },
    "loggers": {
        "django": {
            "handlers": ["console"],
            "level": DJANGO_LOG_LEVEL,
            "propagate": False,
        },
        "django.db.backends": {
            "handlers": ["console"],
            "level": "ERROR",
            "propagate": False,
        },
        "django.security": {
            "handlers": ["console"],
            "level": "WARNING",
            "propagate": False,
        },
    },
}

# Structlog configuration for structured logging
structlog.configure(
    processors=[
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.filter_by_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
        structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
    ],
    logger_factory=structlog.stdlib.LoggerFactory(),
    cache_logger_on_first_use=True,
)

# -----------------------------------------------------
# Sentry (production configuration)
# -----------------------------------------------------
SENTRY_DSN = os.getenv("SENTRY_DSN", "")
if SENTRY_DSN:
    try:
        import sentry_sdk  # type: ignore
        import sentry_sdk.integrations.celery as sentry_celery  # type: ignore
        import sentry_sdk.integrations.django as sentry_django  # type: ignore
        import sentry_sdk.integrations.redis as sentry_redis  # type: ignore

        django_integration_cls = getattr(
            sentry_django,
            "DjangoIntegration",
        )
        celery_integration_cls = getattr(
            sentry_celery,
            "CeleryIntegration",
        )
        redis_integration_cls = getattr(
            sentry_redis,
            "RedisIntegration",
        )

        sentry_sdk.init(  # type: ignore[no-untyped-call]
            dsn=SENTRY_DSN,
            integrations=[
                django_integration_cls(),
                celery_integration_cls(),
                redis_integration_cls(),
            ],
            traces_sample_rate=float(
                os.getenv("SENTRY_TRACES_SAMPLE_RATE", "0.05")
            ),
            profiles_sample_rate=float(
                os.getenv("SENTRY_PROFILES_SAMPLE_RATE", "0.0")
            ),
            environment=os.getenv("SENTRY_ENVIRONMENT", "production"),
            send_default_pii=(
                os.getenv("SENTRY_SEND_PII", "false").lower() == "true"
            ),
            _experiments={
                "continuous_profiling_auto_start": True,
            },
        )
    except ImportError:
        # Skip initialization when the optional Sentry SDK is absent
        pass

print("✅ Production settings loaded successfully")
