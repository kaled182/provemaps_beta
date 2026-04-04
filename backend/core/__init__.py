# Importa a instância do Celery corretamente
from .celery import app as celery_app

__all__ = ("celery_app",)
