"""Management command for idempotent application initialization.

Creates the default superuser and registers essential Celery periodic
tasks via django-celery-beat's DatabaseScheduler.  Safe to run on
every container start — every operation is a no-op when already done.

Environment variables read:
    ADMIN_USERNAME      superuser username        (default: admin)
    ADMIN_EMAIL         superuser email           (default: admin@localhost)
    ADMIN_PASSWORD      superuser password        (default: admin123)
"""
import os
from typing import Any

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Idempotent app initialization: superuser + periodic tasks"

    # ------------------------------------------------------------------
    # Periodic tasks to register with django-celery-beat
    # Each entry: (name, task, schedule_seconds, description)
    # ------------------------------------------------------------------
    PERIODIC_TASKS = [
        (
            "Health-check cleanup",
            "core.tasks.cleanup_old_health_checks",
            60 * 60 * 6,  # every 6 hours
            "Remove stale health-check records older than 7 days",
        ),
        (
            "Cache warmup",
            "core.tasks.warm_cache",
            60 * 30,  # every 30 minutes
            "Pre-populate frequently-accessed cache keys",
        ),
    ]

    def handle(self, *args: Any, **options: Any) -> None:
        self._ensure_superuser()
        self._ensure_periodic_tasks()

    # ------------------------------------------------------------------
    # Superuser
    # ------------------------------------------------------------------
    def _ensure_superuser(self) -> None:
        User = get_user_model()
        username = os.getenv("ADMIN_USERNAME", "admin")
        email = os.getenv("ADMIN_EMAIL", "admin@localhost")
        password = os.getenv("ADMIN_PASSWORD", "admin123")

        if User.objects.filter(username=username).exists():
            self.stdout.write(
                self.style.WARNING(
                    f'[superuser] "{username}" already exists — skipped'
                )
            )
            return

        try:
            User.objects.create_superuser(username, email, password)
            self.stdout.write(
                self.style.SUCCESS(
                    f'[superuser] "{username}" created ({email})'
                )
            )
        except Exception as exc:
            self.stdout.write(
                self.style.ERROR(f"[superuser] failed to create: {exc}")
            )
            raise

    # ------------------------------------------------------------------
    # Periodic tasks (django-celery-beat)
    # ------------------------------------------------------------------
    def _ensure_periodic_tasks(self) -> None:
        try:
            from django_celery_beat.models import (  # type: ignore[import]
                IntervalSchedule,
                PeriodicTask,
            )
        except ImportError:
            self.stdout.write(
                self.style.WARNING(
                    "[periodic] django-celery-beat not installed — skipped"
                )
            )
            return

        for name, task, seconds, _ in self.PERIODIC_TASKS:
            schedule, _ = IntervalSchedule.objects.get_or_create(
                every=seconds,
                period=IntervalSchedule.SECONDS,
            )
            _, created = PeriodicTask.objects.get_or_create(
                name=name,
                defaults={
                    "task": task,
                    "interval": schedule,
                    "enabled": True,
                },
            )
            label = "created" if created else "exists"
            self.stdout.write(
                self.style.SUCCESS(f'[periodic] "{name}" {label}')
            )
