import pymysql

# Garante compatibilidade com MySQL/MariaDB
pymysql.install_as_MySQLdb()

# Importa a instância do Celery corretamente
from .celery_app import app as celery_app  # noqa: E402

__all__ = ("celery_app",)
