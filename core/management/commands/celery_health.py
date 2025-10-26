"""Comando de management para verificar a saúde do Celery.

Uso:
    python manage.py celery_health [--timeout 5]

O comando dispara as tasks `ping` e `health_check` definidas em `core.celery` e
aguarda seus resultados, exibindo um relatório simples.
"""
from __future__ import annotations

import json
import time
from typing import Any
from django.core.management.base import BaseCommand, CommandParser

try:
    # Importa as tasks decoradas; cada uma é um objeto AsyncTask com .delay()
    from core.celery import ping, health_check  # type: ignore
except Exception as e:  # pragma: no cover
    raise SystemExit(f"Erro importando tasks Celery: {e}")


class Command(BaseCommand):
    help = "Verifica se o worker Celery está respondendo corretamente"

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument(
            "--timeout",
            type=int,
            default=5,
            help="Timeout em segundos para aguardar cada task (default: 5)",
        )
        parser.add_argument(
            "--pretty",
            action="store_true",
            help="Imprime JSON formatado do health_check",
        )

    def handle(self, *args: Any, **options: Any) -> str | None:
        timeout: int = options["timeout"]
        started = time.time()

        self.stdout.write("Disparando task ping...")
        async_ping = ping.delay()  # type: ignore[attr-defined]
        self.stdout.write(f"Task ping id={async_ping.id}")

        try:
            pong = async_ping.get(timeout=timeout)
        except Exception as e:  # pragma: no cover
            self.stderr.write(
                self.style.ERROR(f"Falha no ping: {e}")
            )
            return None

        if pong != "pong":  # pragma: no cover
            self.stderr.write(
                self.style.ERROR(
                    f"Resposta inesperada do ping: {pong}"
                )
            )
            return None

        self.stdout.write(self.style.SUCCESS("Ping OK (pong)"))

        self.stdout.write("Disparando task health_check...")
        async_health = health_check.delay()  # type: ignore[attr-defined]
        self.stdout.write(f"Task health_check id={async_health.id}")

        try:
            health: dict[str, Any] = async_health.get(timeout=timeout)
        except Exception as e:  # pragma: no cover
            self.stderr.write(self.style.ERROR(f"Falha no health_check: {e}"))
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
                f"Verificação concluída em {elapsed:.2f}s"
            )
        )
        return None
