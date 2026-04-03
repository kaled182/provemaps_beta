from __future__ import annotations

from django.core.management.base import BaseCommand

from inventory.models import FiberCable
from inventory.domain.geometry import (
    calculate_path_length,
    sanitize_path_points,
)


class Command(BaseCommand):
    help = (
        "Backfill length_km for FiberCable entries using path_coordinates. "
        "Only updates records where length_km is NULL and path_coordinates has >= 2 points."
    )

    def handle(self, *args, **options):
        updated = 0
        total_candidates = 0
        for cable in FiberCable.objects.all():
            if cable.length_km is not None:
                continue
            if not cable.path_coordinates:
                continue
            sanitized = sanitize_path_points(cable.path_coordinates, allow_empty=False)
            if len(sanitized) < 2:
                continue
            total_candidates += 1
            length_km = calculate_path_length(sanitized)
            cable.length_km = length_km
            cable.save(update_fields=["length_km"])
            updated += 1
            self.stdout.write(
                self.style.SUCCESS(
                    f"Updated cable {cable.id} ({cable.name}) length_km={length_km:.2f}"
                )
            )

        self.stdout.write(
            self.style.NOTICE(
                f"Backfill complete. Candidates: {total_candidates}, Updated: {updated}"
            )
        )
