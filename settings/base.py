"""
Settings base para o projeto mapsprovefiber.
- Não específica de ambiente (dev/prod); overrides vão em settings.dev / settings.prod.
- Mantém defaults seguros e neutros; sem dependência obrigatória de Redis.
"""

import os
from pathlib import Path

# -----------------------------------------------------
# Paths / núcleo
# -----------------------------------------------------
BASE_DIR = Path(__file__).resolve().parent.parent
SECRET_KEY = os.getenv("SECRET_KEY")

if not SECRET_KEY:
    settings_module = os.getenv("DJANGO_SETTINGS_MODULE", "")
    if settings_module.endswith(".test"):
        SECRET_KEY = "test-only-insecure-key"
    elif os.getenv("DEBUG", "False").lower() == "true":
        SECRET_KEY = "dev-only-insecure-key-for-development"
    else:
        raise ValueError("SECRET_KEY must be set in production")

DEBUG = os.getenv("DEBUG", "False").lower() == "true"
ALLOWED_HOSTS = [h.strip() for h in os.getenv("ALLOWED_HOSTS", "localhost,127.0.0.1").split(",") if h.strip()]

ZABBIX_API_URL = os.getenv("ZABBIX_API_URL", "")
ZABBIX_API_USER = os.getenv("ZABBIX_API_USER", "")
ZABBIX_API_PASSWORD = os.getenv("ZABBIX_API_PASSWORD", "")
ZABBIX_API_KEY = os.getenv("ZABBIX_API_KEY", "")
GOOGLE_MAPS_API_KEY = os.getenv("GOOGLE_MAPS_API_KEY", "")
ENABLE_DIAGNOSTIC_ENDPOINTS = os.getenv("ENABLE_DIAGNOSTIC_ENDPOINTS", "False").lower() == "true"

FERNET_KEYS = [key.strip() for key in os.getenv("FERNET_KEYS", "").split(",") if key.strip()]
if not FERNET_KEYS:
    single_fernet = os.getenv("FERNET_KEY")
    if single_fernet:
        FERNET_KEYS = [single_fernet]
if not FERNET_KEYS:
    FERNET_KEYS = [SECRET_KEY]

# Security defaults
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = "DENY"
CSRF_TRUSTED_ORIGINS = [
    origin.strip()
    for origin in os.getenv("CSRF_TRUSTED_ORIGINS", "").split(",")
    if origin.strip()
]

# Segurança adicional apenas quando não está em DEBUG
if not DEBUG:
    SECURE_SSL_REDIRECT = os.getenv("SECURE_SSL_REDIRECT", "True").lower() == "true"
    SECURE_HSTS_SECONDS = int(os.getenv("SECURE_HSTS_SECONDS", "31536000"))  # 1 ano
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True

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

    # Observabilidade
    "django_prometheus",

    # Realtime / WebSockets
    "channels",

    # Apps do projeto
    "core",
    "maps_view",
    "routes_builder",
    "setup_app",
    "zabbix_api",
]

MIDDLEWARE = [
    "django_prometheus.middleware.PrometheusBeforeMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "django_prometheus.middleware.PrometheusAfterMiddleware",
]

ROOT_URLCONF = "core.urls"
WSGI_APPLICATION = "core.wsgi.application"
ASGI_APPLICATION = "core.asgi.application"

# -----------------------------------------------------
# Database (MySQL/MariaDB com fallbacks) — otimizado
# -----------------------------------------------------
DB_OPTIONS = {
    "charset": "utf8mb4",
    "init_command": "SET sql_mode='STRICT_ALL_TABLES'",
    "connect_timeout": 10,
}

# Pool opcional (quando disponível via driver)
if os.getenv("DB_USE_CONNECTION_POOL", "false").lower() == "true":
    DB_OPTIONS.update({
        "pool_size": int(os.getenv("DB_POOL_SIZE", "10")),
        "max_overflow": int(os.getenv("DB_MAX_OVERFLOW", "20")),
        "pool_pre_ping": True,
        "pool_recycle": 300,
    })

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.mysql",
        "NAME": os.getenv("DB_NAME", "app"),
        "USER": os.getenv("DB_USER", "app"),
        "PASSWORD": os.getenv("DB_PASSWORD", "app"),
        "HOST": os.getenv("DB_HOST", "127.0.0.1"),
        "PORT": os.getenv("DB_PORT", "3306"),
        "OPTIONS": DB_OPTIONS,
        "CONN_MAX_AGE": int(os.getenv("DB_CONN_MAX_AGE", "0")),
        "ATOMIC_REQUESTS": os.getenv("DB_ATOMIC_REQUESTS", "false").lower() == "true",
    }
}

# -----------------------------------------------------
# Cache (Redis se disponível; senão fallback robusto)
# -----------------------------------------------------
REDIS_URL = os.getenv("REDIS_URL", "").strip()

def get_cache_config():
    """Retorna configuração de cache baseada na disponibilidade do Redis."""
    if REDIS_URL:
        return {
            "default": {
                "BACKEND": "django_redis.cache.RedisCache",
                "LOCATION": REDIS_URL,
                "OPTIONS": {
                    "CLIENT_CLASS": "django_redis.client.DefaultClient",
                    "COMPRESSOR": "django_redis.compressors.zlib.ZlibCompressor",
                    "SOCKET_CONNECT_TIMEOUT": 5,
                    "SOCKET_TIMEOUT": 5,
                    "RETRY_ON_TIMEOUT": True,
                    "MAX_CONNECTIONS": int(os.getenv("REDIS_MAX_CONNECTIONS", "100")),
                },
                "KEY_PREFIX": "mapsprovefiber",
                "VERSION": 1,
            }
        }
    else:
        # Em produção sem Redis, usa filebased; em dev, locmem
        if not DEBUG:
            return {
                "default": {
                    "BACKEND": "django.core.cache.backends.filebased.FileBasedCache",
                    "LOCATION": "/tmp/django_cache",
                    "TIMEOUT": 300,
                    "OPTIONS": {"MAX_ENTRIES": 1000},
                }
            }
        else:
            return {
                "default": {
                    "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
                    "LOCATION": "mapsprovefiber-local",
                }
            }

CACHES = get_cache_config()

# Sessões
if REDIS_URL:
    SESSION_ENGINE = "django.contrib.sessions.backends.cache"
    SESSION_CACHE_ALIAS = "default"
    SESSION_COOKIE_AGE = int(os.getenv("SESSION_COOKIE_AGE", "1209600"))  # 2 semanas
else:
    SESSION_ENGINE = "django.contrib.sessions.backends.db"

# -----------------------------------------------------
# ASGI / Channels (WebSockets)
# -----------------------------------------------------
CHANNEL_LAYER_URL = os.getenv("CHANNEL_LAYER_URL", os.getenv("REDIS_URL", "")).strip()
CHANNEL_PREFIX = os.getenv("CHANNEL_REDIS_PREFIX", "mapsprovefiber")

if CHANNEL_LAYER_URL.startswith(("redis://", "rediss://")):
    CHANNEL_LAYERS = {
        "default": {
            "BACKEND": "channels_redis.core.RedisChannelLayer",
            "CONFIG": {
                "hosts": [CHANNEL_LAYER_URL],
                "prefix": CHANNEL_PREFIX,
            },
        }
    }
else:
    CHANNEL_LAYERS = {
        "default": {
            "BACKEND": "channels.layers.InMemoryChannelLayer",
        }
    }

# -----------------------------------------------------
# Internacionalização / TZ
# -----------------------------------------------------
LANGUAGE_CODE = os.getenv("LANGUAGE_CODE", "pt-br")
TIME_ZONE = os.getenv("TIME_ZONE", "America/Belem")
USE_I18N = True
USE_TZ = True

# -----------------------------------------------------
# Arquivos estáticos / mídia
# -----------------------------------------------------
STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# -----------------------------------------------------
# Templates (com cache em produção)
# -----------------------------------------------------
TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

if not DEBUG:
    # Ativa template caching em produção
    TEMPLATES[0]["OPTIONS"]["loaders"] = [
        (
            "django.template.loaders.cached.Loader",
            [
                "django.template.loaders.filesystem.Loader",
                "django.template.loaders.app_directories.Loader",
            ],
        )
    ]

# -----------------------------------------------------
# Health Check Configuration
# -----------------------------------------------------
HEALTHCHECK_CONFIG = {
    "DISK_THRESHOLD_GB": float(os.getenv("HEALTHCHECK_DISK_THRESHOLD_GB", "1.0")),
    "DB_TIMEOUT": int(os.getenv("HEALTHCHECK_DB_TIMEOUT", "5")),
    "ENABLE_STORAGE_CHECK": os.getenv("HEALTHCHECK_STORAGE", "true").lower() == "true",
    "ENABLE_SYSTEM_METRICS": os.getenv("HEALTHCHECK_SYSTEM_METRICS", "false").lower() == "true",
    "DEBUG": os.getenv("HEALTHCHECK_DEBUG", "false").lower() == "true",
}

# -----------------------------------------------------
# Logging (com rotação opcional)
# -----------------------------------------------------
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
LOG_FORMAT = os.getenv("LOG_FORMAT", "verbose")  # "simple" ou "verbose"

FORMATTERS = {
    "verbose": {
        "format": "{levelname} {asctime} {module} {process:d} {thread:d} {message}",
        "style": "{",
    },
    "simple": {
        "format": "{levelname} {asctime} {message}",
        "style": "{",
    },
}

HANDLERS = {
    "console": {
        "class": "logging.StreamHandler",
        "formatter": LOG_FORMAT,
    },
}

# File handler opcional (somente produção, se habilitado)
if not DEBUG and os.getenv("ENABLE_FILE_LOGGING", "false").lower() == "true":
    HANDLERS["file"] = {
        "class": "logging.handlers.RotatingFileHandler",
        "filename": os.getenv("LOG_FILE", "/var/log/django/app.log"),
        "maxBytes": int(os.getenv("LOG_MAX_BYTES", "10485760")),  # 10MB
        "backupCount": int(os.getenv("LOG_BACKUP_COUNT", "5")),
        "formatter": LOG_FORMAT,
    }

LOGGING = {
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

# Log detalhado de queries (opcional)
if os.getenv("ENABLE_DB_QUERY_LOG", "false").lower() == "true":
    LOGGING["loggers"]["django.db.backends"] = {
        "level": "DEBUG",
        "handlers": ["console"],
        "propagate": False,
    }

# -----------------------------------------------------
# Monitoring (Sentry - opcional)
# -----------------------------------------------------
SENTRY_DSN = os.getenv("SENTRY_DSN", "")
if SENTRY_DSN:
    import sentry_sdk
    from sentry_sdk.integrations.django import DjangoIntegration
    from sentry_sdk.integrations.celery import CeleryIntegration

    sentry_sdk.init(
        dsn=SENTRY_DSN,
        integrations=[DjangoIntegration(), CeleryIntegration()],
        traces_sample_rate=float(os.getenv("SENTRY_TRACES_SAMPLE_RATE", "0.1")),
        profiles_sample_rate=float(os.getenv("SENTRY_PROFILES_SAMPLE_RATE", "0.0")),
        environment=os.getenv("SENTRY_ENVIRONMENT", "development"),
        debug=DEBUG,
    )
