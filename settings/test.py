"""
Settings para TESTES do mapsprovefiber.
Usa MariaDB (Docker) para ambiente de teste próximo à produção.
"""

from .base import *  # noqa
import os

# -----------------------------------------------------
# Configurações de Teste
# -----------------------------------------------------
DEBUG = False
TESTING = True
# Evita redirecionamentos HTTP->HTTPS em testes
SECURE_SSL_REDIRECT = False

# Banco de dados
# - Por padrão usamos SQLite em disco para reduzir dependências externas durante o pytest.
# - Defina TEST_DB_ENGINE=mysql para reutilizar o container MariaDB (docker-compose).
if os.getenv("TEST_DB_ENGINE", "").lower() == "mysql":
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.mysql",
            "NAME": os.getenv("DB_NAME", "app"),
            "USER": os.getenv("DB_USER", "app"),
            "PASSWORD": os.getenv("DB_PASSWORD", "app"),
            "HOST": os.getenv("DB_HOST", "db"),
            "PORT": os.getenv("DB_PORT", "3306"),
            "TEST": {
                "CHARSET": "utf8mb4",
                "COLLATION": "utf8mb4_unicode_ci",
            },
            "OPTIONS": {
                "init_command": "SET sql_mode='STRICT_TRANS_TABLES'",
                "charset": "utf8mb4",
            },
        }
    }
    print("[TEST] Environment loaded - MySQL backend")
else:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / "test_db.sqlite3",
        }
    }
    print("[TEST] Environment loaded - SQLite backend")

# Hash mais rápido (evita lentidão com bcrypt/argon2)
PASSWORD_HASHERS = [
    "django.contrib.auth.hashers.MD5PasswordHasher",
]

# Cache e sessões locais
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        "LOCATION": "test-cache",
    }
}
SESSION_ENGINE = "django.contrib.sessions.backends.cache"

# E-mail capturado em memória (não enviado)
EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"

# Logging silencioso (não polui saída de pytest)
LOGGING = {
    "version": 1,
    "disable_existing_loggers": True,
    "handlers": {"null": {"class": "logging.NullHandler"}},
    "root": {"handlers": ["null"], "level": "CRITICAL"},
}

# Prometheus desativado em testes
INSTALLED_APPS = [app for app in INSTALLED_APPS if app != "django_prometheus"]

# Static & Media isolados
STATICFILES_STORAGE = "django.contrib.staticfiles.storage.StaticFilesStorage"
MEDIA_ROOT = BASE_DIR / "test_media"
