import statistics
import time
from argparse import ArgumentParser
from typing import Any

from django.core.management.base import BaseCommand, CommandError
from django.test import Client
from django.urls import reverse

from inventory.models import Device, FiberCable, Port


class Command(BaseCommand):
    help = (
        "Run sample requests against critical endpoints and report latency"
        " metrics."
    )

    def add_arguments(self, parser: ArgumentParser) -> None:
        parser.add_argument(
            "--username",
            required=True,
            help="User allowed to access the protected endpoints.",
        )
        parser.add_argument(
            "--password",
            required=True,
            help="Password for the provided user.",
        )
        parser.add_argument(
            "--runs",
            type=int,
            default=5,
            help="Number of requests to perform per endpoint (default: 5).",
        )

    def handle(self, *args: Any, **options: Any) -> None:
        username = options["username"]
        password = options["password"]
        runs = options["runs"]

        client = Client()
        client.defaults["HTTP_HOST"] = "localhost"

        if not client.login(username=username, password=password):
            raise CommandError(
                "Authentication failed. Check username/password."
            )

        # Select representative examples for each endpoint type
        device: Device | None = Device.objects.order_by("id").first()
        port: Port | None = Port.objects.order_by("id").first()
        cable: FiberCable | None = FiberCable.objects.order_by("id").first()

        endpoints: list[tuple[str, str, str, dict[str, Any] | None]] = [
            (
                "fibers",
                "get",
                reverse("inventory-api:fibers"),
                None,
            ),
            (
                "sites",
                "get",
                reverse("inventory-api:sites"),
                None,
            ),
        ]

        if device:
            assert device is not None
            device_id = int(device.pk)
            endpoints.append(
                (
                    "device-ports",
                    "get",
                    reverse(
                        "inventory-api:device-ports",
                        args=[device_id],
                    ),
                    None,
                )
            )
        if port:
            assert port is not None
            port_id = int(port.pk)
            endpoints.append(
                (
                    "port-optical-status",
                    "get",
                    reverse(
                        "inventory-api:port-optical-status",
                        args=[port_id],
                    ),
                    None,
                )
            )
        if cable:
            assert cable is not None
            cable_id = int(cable.pk)
            endpoints.append(
                (
                    "fiber-detail",
                    "get",
                    reverse(
                        "inventory-api:fiber-detail",
                        args=[cable_id],
                    ),
                    None,
                )
            )

        self.stdout.write(
            self.style.NOTICE(f"Executing {runs} request(s) per endpoint...\n")
        )
        header = (
            f"{'Endpoint':25} {'Status':7} {'Avg(ms)':>10} "
            f"{'P95(ms)':>10} {'Max(ms)':>10}"
        )
        self.stdout.write(header)
        self.stdout.write("-" * len(header))

        for name, method, path, payload in endpoints:
            durations: list[float] = []
            last_status: int | None = None

            for _ in range(runs):
                start = time.perf_counter()
                response = getattr(client, method)(path, data=payload or {})
                elapsed = (time.perf_counter() - start) * 1000
                durations.append(elapsed)
                last_status = response.status_code

            avg = statistics.mean(durations)
            if len(durations) > 1:
                sorted_durations = sorted(durations)
                index = max(0, int(round(0.95 * (len(sorted_durations) - 1))))
                p95 = sorted_durations[index]
            else:
                p95 = durations[0]
            max_v = max(durations)

            self.stdout.write(
                f"{name:25} {last_status!s:7} {avg:10.1f} "
                f"{p95:10.1f} {max_v:10.1f}"
            )

        self.stdout.write(
            "\nDone. Use these metrics as a baseline for future comparisons."
        )
