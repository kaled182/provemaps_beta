"""Management command that checks whether Celery workers are healthy.

Usage:
    python manage.py celery_health [--timeout 5]

The command triggers the `ping` and `health_check` tasks from ``core.celery``
and waits for their results, printing a short status report.
"""
from __future__ import annotations

import json
import time
from typing import Any
from django.core.management.base import BaseCommand, CommandParser

try:
    # Import decorated tasks; each is an AsyncTask object with .delay()
    from core.celery import ping, health_check  # type: ignore
except Exception as e:  # pragma: no cover
    raise SystemExit(f"Error importing Celery tasks: {e}")


class Command(BaseCommand):
    help = "Check whether the Celery worker responds correctly"

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument(
            "--timeout",
            type=int,
            default=5,
            help="Seconds to wait for each task (default: 5)",
        )
        parser.add_argument(
            "--pretty",
            action="store_true",
            help="Pretty-print the health_check JSON payload",
        )

    def handle(self, *args: Any, **options: Any) -> str | None:
        timeout: int = options["timeout"]
        started = time.time()

        self.stdout.write("Triggering ping task...")
        async_ping = ping.delay()  # type: ignore[attr-defined]
        self.stdout.write(f"Task ping id={async_ping.id}")

        try:
            pong = async_ping.get(timeout=timeout)
        except Exception as e:  # pragma: no cover
            self.stderr.write(
                self.style.ERROR(f"Ping failed: {e}")
            )
            return None

        if pong != "pong":  # pragma: no cover
            self.stderr.write(
                self.style.ERROR(
                    f"Unexpected ping response: {pong}"
                )
            )
            return None

        self.stdout.write(self.style.SUCCESS("Ping OK (pong)"))

        self.stdout.write("Triggering health_check task...")
        async_health = health_check.delay()  # type: ignore[attr-defined]
        self.stdout.write(f"Task health_check id={async_health.id}")

        try:
            health: dict[str, Any] = async_health.get(timeout=timeout)
        except Exception as e:  # pragma: no cover
            self.stderr.write(self.style.ERROR(f"health_check failed: {e}"))
            return None

        if options["pretty"]:
            formatted = json.dumps(health, indent=2, ensure_ascii=False)
            self.stdout.write(formatted)
        else:
            self.stdout.write(
                "Status: {s} | Broker: {b} | Worker: {w}".format(
                    s=health.get("status"),
                    b=health.get("broker_connected"),
                    w=health.get("worker_id"),
                )
            )

        elapsed = time.time() - started
        self.stdout.write(
            self.style.SUCCESS(
                f"Verification completed in {elapsed:.2f}s"
            )
        )
        return None
