"""
Management command to populate Fibracem SVT splice box templates.
Creates the standard 24, 48, 72, and 96 fiber capacity models.
"""
from django.core.management.base import BaseCommand
from inventory.models import SpliceBoxTemplate


class Command(BaseCommand):
    help = 'Popula templates de caixas de emenda Fibracem SVT (24-96FO)'

    def handle(self, *args, **kwargs):
        """Create standard Fibracem SVT templates based on manufacturer specs."""
        templates = [
            # (Nome, Max Bandejas, Fusões/Bandeja, Comprimento mm, Diâmetro mm)
            ("SVT 24 Fibras", 1, 24, 492, 195),
            ("SVT 48 Fibras", 2, 24, 492, 195),
            ("SVT 72 Fibras", 3, 24, 492, 195),
            ("SVT 96 Fibras", 4, 24, 492, 195),
        ]

        created_count = 0
        updated_count = 0

        for name, trays, splices, length, diameter in templates:
            obj, created = SpliceBoxTemplate.objects.update_or_create(
                name=name,
                manufacturer='Fibracem',
                defaults={
                    'model_code': 'SVT',
                    'max_trays': trays,
                    'splices_per_tray': splices,
                    'cable_ports_oval': 1,
                    'cable_ports_round': 4,
                    'length_mm': length,
                    'diameter_mm': diameter,
                }
            )

            if created:
                created_count += 1
                self.stdout.write(
                    self.style.SUCCESS(
                        f'✓ Criado: {name} ({trays}x{splices} = {trays * splices}FO)'
                    )
                )
            else:
                updated_count += 1
                self.stdout.write(
                    f'  Atualizado: {name}'
                )

        self.stdout.write('')
        self.stdout.write(
            self.style.SUCCESS(
                f'Concluído! {created_count} criados, {updated_count} atualizados'
            )
        )
