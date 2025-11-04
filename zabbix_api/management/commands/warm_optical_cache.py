from __future__ import annotations

from argparse import ArgumentParser
from typing import Any, cast

from django.core.management.base import BaseCommand

from inventory.models import Device, Port
from zabbix_api.domain import optical as optical_domain
from zabbix_api.tasks import warm_port_optical_cache

fetch_port_optical_snapshot = getattr(
    optical_domain,
    "fetch_port_optical_snapshot",
)


class Command(BaseCommand):
    help = "Warm the optical power (RX/TX) cache for monitored ports."

    def add_arguments(self, parser: ArgumentParser) -> None:
        parser.add_argument(
            "--device-id",
            type=int,
            help="Limit the warm-up process to a single device.",
        )
        parser.add_argument(
            "--async",
            dest="async_mode",
            action="store_true",
            help=(
                "Dispatch the warm-up tasks to Celery "
                "instead of running inline."
            ),
        )

    def handle(self, *args: Any, **options: Any) -> None:
        device_id = options.get("device_id")
        async_mode = options.get("async_mode")

        if device_id:
            devices = Device.objects.filter(id=device_id)
            if not devices.exists():
                self.stderr.write(
                    self.style.ERROR(f"Device {device_id} not found.")
                )
                return
        else:
            devices = Device.objects.all()

        total_ports = 0
        for device in devices:
            ports = Port.objects.select_related("device").filter(device=device)
            for port in ports:
                total_ports += 1
                if async_mode:
                    cast(Any, warm_port_optical_cache).delay(port.pk)
                else:
                    fetch_port_optical_snapshot(
                        port,
                        discovery_cache={},
                        persist_keys=False,
                    )

        if async_mode:
            self.stdout.write(
                self.style.SUCCESS(
                    f"Queued warm-up tasks for {total_ports} ports."
                )
            )
            self.stdout.write(
                "Start a Celery worker: celery -A core worker -l info"
            )
        else:
            self.stdout.write(
                self.style.SUCCESS(
                    f"Optical cache refreshed for {total_ports} ports."
                )
            )
