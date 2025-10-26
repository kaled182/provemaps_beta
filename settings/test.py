"""
Settings para TESTES do mapsprovefiber.
Isola dependências externas e acelera a execução dos testes.
"""

from .base import *  # noqa

# -----------------------------------------------------
# Configurações de Teste
# -----------------------------------------------------
DEBUG = False
TESTING = True
# Evita redirecionamentos HTTP->HTTPS em testes
SECURE_SSL_REDIRECT = False

# Banco de dados em memória
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": ":memory:",
    }
}

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

print("🧪 Ambiente de TESTES carregado (SQLite em memória)")
