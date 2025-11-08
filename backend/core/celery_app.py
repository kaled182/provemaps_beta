"""Celery application shim module.

Allows docker-compose commands to use `-A core.celery_app` while the actual
Celery instance lives in `core/celery.py`.

Celery will look for a variable named `app` (or `celery`) in the target module.
We simply re-export the existing instance from `core.celery`.
"""
from .celery import app

__all__ = ["app"]
