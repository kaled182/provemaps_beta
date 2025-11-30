from django.core.management.base import BaseCommand

from inventory.models import SpliceBoxTemplate


TEMPLATES = [
    ("CEO SVT 24 Fibras", 1, 24),
    ("CEO SVT 48 Fibras", 2, 24),
    ("CEO SVT 72 Fibras", 3, 24),
    ("CEO SVT 96 Fibras", 4, 24),
]


class Command(BaseCommand):
    help = "Seed Fibracem SVT SpliceBox templates (24/48/72/96)"

    def handle(self, *args, **options):
        created = 0
        for name, trays, splices in TEMPLATES:
            _, was_created = SpliceBoxTemplate.objects.get_or_create(
                name=name,
                defaults={
                    "manufacturer": "Fibracem",
                    "max_trays": trays,
                    "splices_per_tray": splices,
                    "cable_ports_oval": 1,
                    "cable_ports_round": 4,
                },
            )
            if was_created:
                created += 1
        self.stdout.write(
            self.style.SUCCESS(
                f"Seed completed: {created} new templates (SVT 24/48/72/96)."
            )
        )
