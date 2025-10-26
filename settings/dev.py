"""
Settings de DESENVOLVIMENTO para o mapsprovefiber.
Herdam de settings.base e aplicam apenas overrides seguros para Dev.
"""

import os
from .base import *  # noqa

# -----------------------------------------------------
# Núcleo
# -----------------------------------------------------
DEBUG = True

# Hosts de desenvolvimento (inclui Docker/compose)
ALLOWED_HOSTS = [
    "localhost",
    "127.0.0.1", 
    "0.0.0.0",
    "web",                    # nome do serviço no docker-compose
    "host.docker.internal",   # para acessar host do Docker
]

# CSRF em dev 
CSRF_TRUSTED_ORIGINS = [
    "http://localhost:8000",
    "http://127.0.0.1:8000",
    "http://0.0.0.0:8000",
    "http://web:8000",
]

# Email sai no console
EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"

# -----------------------------------------------------
# Database (Dev optimizations)
# -----------------------------------------------------
# Conexões curtas para desenvolvimento
DATABASES["default"]["CONN_MAX_AGE"] = 0
DATABASES["default"]["OPTIONS"].update({
    "connect_timeout": 3,
})

# Fallback para SQLite se especificado
if os.getenv("DB_ENGINE") == "sqlite":
    DATABASES["default"] = {
        "ENGINE": "django.db.backends.sqlite3", 
        "NAME": BASE_DIR / "db.sqlite3",
    }

# -----------------------------------------------------
# Logging (Dev-friendly)
# -----------------------------------------------------
LOG_LEVEL = "DEBUG"

# Configura logging para desenvolvimento
LOGGING["formatters"]["verbose"] = {
    "format": "{levelname} {asctime} {module} {message}",
    "style": "{",
}

LOGGING["root"]["level"] = LOG_LEVEL
LOGGING["loggers"]["django"]["level"] = "INFO"
LOGGING["loggers"]["django.db.backends"] = {
    "level": "INFO",  # Mude para DEBUG para ver queries SQL
    "handlers": ["console"],
    "propagate": False,
}

# -----------------------------------------------------
# Debug Toolbar (Auto-configure)
# -----------------------------------------------------
try:
    import debug_toolbar  # noqa
    INSTALLED_APPS += ["debug_toolbar"]
    MIDDLEWARE.insert(0, "debug_toolbar.middleware.DebugToolbarMiddleware")
    DEBUG_TOOLBAR_CONFIG = {"SHOW_TOOLBAR_CALLBACK": lambda request: True}
    INTERNAL_IPS = ["127.0.0.1", "localhost", "0.0.0.0", "172.16.0.0/12"]
    print("[DEBUG_TOOLBAR] Django Debug Toolbar habilitado")
except ImportError:
    print("[INFO] Django Debug Toolbar nao instalado")
except Exception as e:
    print(f"[WARN] Erro ao configurar Debug Toolbar: {e}")


# -----------------------------------------------------
# Development-specific
# -----------------------------------------------------

# Static files em dev (Manifest para gerar hash por conteúdo)
STATICFILES_STORAGE = "django.contrib.staticfiles.storage.ManifestStaticFilesStorage"

import time as _time  # noqa: E402
import subprocess  # noqa: E402

def _git_sha():
    """Retorna SHA curto do commit atual ou 'nosha' se indisponível."""
    try:
        sha = subprocess.check_output([
            "git", "rev-parse", "--short", "HEAD"
        ], cwd=BASE_DIR).decode().strip()
        if sha:
            return sha
    except Exception:
        return "nosha"
    return "nosha"

# sha-timestamp para cache bust e rastreabilidade
STATIC_ASSET_VERSION = f"{_git_sha()}-{_time.strftime('%Y%m%d%H%M%S')}"
print(f"[STATIC_VERSION] STATIC_ASSET_VERSION={STATIC_ASSET_VERSION}")

# Middleware no-cache para rotas sensíveis
MIDDLEWARE.append('core.middleware.no_cache_dev.NoCacheDevMiddleware')

# Security relaxations for development
if DEBUG:
    SECURE_SSL_REDIRECT = False
    SESSION_COOKIE_SECURE = False  
    CSRF_COOKIE_SECURE = False
    
    # Template debugging
    TEMPLATES[0]["OPTIONS"]["debug"] = True

# -----------------------------------------------------
# Development Tools (Optional)
# -----------------------------------------------------

# Django Extensions (se instalado)
try:
    import django_extensions  # noqa
    INSTALLED_APPS += ["django_extensions"]
    print("[DJANGO_EXTENSIONS] Habilitado")
except ImportError:
    pass

# Shell plus configuration
SHELL_PLUS = "ipython"
SHELL_PLUS_PRINT_SQL = True

print(f"[DEV] Ambiente de DESENVOLVIMENTO carregado - DEBUG={DEBUG}")