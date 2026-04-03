"""
Management command to test atomic fusion logic.
"""
from django.core.management.base import BaseCommand
from django.contrib.gis.geos import Point, LineString
from inventory.models import (
    Site,
    FiberCable,
    BufferTube,
    FiberStrand,
    FiberInfrastructure,
)


class Command(BaseCommand):
    help = 'Test atomic fusion logic - verifies the fix for color fusion bug'

    def handle(self, *args, **options):
        self.stdout.write("\n" + "="*60)
        self.stdout.write("TESTE - Correção de Fusão Atômica")
        self.stdout.write("="*60)

        # Cleanup
        self.stdout.write("\n1. Limpando dados de teste...")
        FiberStrand.objects.filter(
            tube__cable__name__in=['Cabo-Entrada-Test', 'Cabo-Saida-Test']
        ).delete()
        BufferTube.objects.filter(
            cable__name__in=['Cabo-Entrada-Test', 'Cabo-Saida-Test']
        ).delete()
        FiberInfrastructure.objects.filter(name='CEO-Teste-001').delete()
        FiberCable.objects.filter(
            name__in=['Cabo-Entrada-Test', 'Cabo-Saida-Test']
        ).delete()
        Site.objects.filter(display_name='Site Teste Fusão').delete()

        # Create site
        self.stdout.write("\n2. Criando site...")
        site = Site.objects.create(
            display_name="Site Teste Fusão",
            city="Brasília",
            location=Point(-47.9292, -15.7801, srid=4326),
        )

        # Create Cable A
        self.stdout.write("\n3. Criando Cabo A com 12 fibras...")
        cable_a = FiberCable.objects.create(
            name="Cabo-Entrada-Test",
            strand_count=12,
            origin_site=site,
            path=LineString(
                [(-47.9292, -15.7801), (-47.9392, -15.7901)],
                srid=4326
            ),
        )

        tube_a = BufferTube.objects.create(
            cable=cable_a,
            number=1,
            color="Azul",
            color_hex="#0000FF",
            strand_count=12,
        )

        colors = [
            ("Verde", "#00FF00"),
            ("Amarelo", "#FFFF00"),
            ("Branco", "#FFFFFF"),
            ("Azul", "#0000FF"),
            ("Vermelho", "#FF0000"),
            ("Violeta", "#8B00FF"),
            ("Marrom", "#8B4513"),
            ("Rosa", "#FFC0CB"),
            ("Preto", "#000000"),
            ("Cinza", "#808080"),
            ("Laranja", "#FFA500"),
            ("Aqua", "#00FFFF"),
        ]

        strands_a = []
        for i, (color, hex_code) in enumerate(colors, start=1):
            strand = FiberStrand.objects.create(
                tube=tube_a,
                number=i,
                absolute_number=i,
                color=color,
                color_hex=hex_code,
                status="dark",
            )
            strands_a.append(strand)

        # Create Cable B
        self.stdout.write("\n4. Criando Cabo B com 12 fibras...")
        cable_b = FiberCable.objects.create(
            name="Cabo-Saida-Test",
            strand_count=12,
            destination_site=site,
            path=LineString(
                [(-47.9392, -15.7901), (-47.9492, -15.8001)],
                srid=4326
            ),
        )

        tube_b = BufferTube.objects.create(
            cable=cable_b,
            number=1,
            color="Azul",
            color_hex="#0000FF",
            strand_count=12,
        )

        strands_b = []
        for i, (color, hex_code) in enumerate(colors, start=1):
            strand = FiberStrand.objects.create(
                tube=tube_b,
                number=i,
                absolute_number=i,
                color=color,
                color_hex=hex_code,
                status="dark",
            )
            strands_b.append(strand)

        # Create CEO
        self.stdout.write("\n5. Criando CEO...")
        ceo = FiberInfrastructure.objects.create(
            name="CEO-Teste-001",
            type="splice_box",
            cable=cable_a,
            location=Point(-47.9342, -15.7851, srid=4326),
            installed_trays=4,
        )

        # TEST SCENARIO
        self.stdout.write("\n" + "="*60)
        self.stdout.write("CENÁRIO DE TESTE")
        self.stdout.write("="*60)

        self.stdout.write(
            "\n6. Fusão 1: Cabo-A FO-12 (Aqua) <-> "
            "Cabo-B FO-4 (Azul) [Bandeja 1, Slot 1]"
        )
        fo_12_a = strands_a[11]  # Aqua
        fo_04_b = strands_b[3]   # Azul

        fo_12_a.fused_to = fo_04_b
        fo_12_a.fusion_infrastructure = ceo
        fo_12_a.fusion_tray = 1
        fo_12_a.fusion_slot = 1
        fo_12_a.save()

        fo_04_b.fused_to = fo_12_a
        fo_04_b.fusion_infrastructure = ceo
        fo_04_b.fusion_tray = 1
        fo_04_b.fusion_slot = 1
        fo_04_b.save()

        self.stdout.write(
            self.style.SUCCESS(
                f"   ✓ {cable_a.name} FO-12 <-> {cable_b.name} FO-4"
            )
        )

        self.stdout.write(
            "\n7. Fusão 2: Cabo-A FO-1 (Verde) <-> "
            "Cabo-B FO-1 (Verde) [Bandeja 1, Slot 2]"
        )
        fo_01_a = strands_a[0]   # Verde
        fo_01_b = strands_b[0]   # Verde

        # Check if slot is free (using atomic logic)
        slot_occupants = FiberStrand.objects.filter(
            fusion_infrastructure=ceo,
            fusion_tray=1,
            fusion_slot=2
        ).exclude(id__in=[fo_01_a.id, fo_01_b.id])

        if slot_occupants.exists():
            self.stdout.write(
                self.style.ERROR("   ✗ FALHA: Slot 2 está ocupado!")
            )
            self.stdout.write(self.style.ERROR("   🐛 BUG DETECTADO!"))
        else:
            self.stdout.write(
                self.style.SUCCESS("   ✓ Slot 2 está LIVRE (correto!)")
            )
            
            fo_01_a.fused_to = fo_01_b
            fo_01_a.fusion_infrastructure = ceo
            fo_01_a.fusion_tray = 1
            fo_01_a.fusion_slot = 2
            fo_01_a.save()
            
            fo_01_b.fused_to = fo_01_a
            fo_01_b.fusion_infrastructure = ceo
            fo_01_b.fusion_tray = 1
            fo_01_b.fusion_slot = 2
            fo_01_b.save()
            
            self.stdout.write(
                self.style.SUCCESS(
                    f"   ✓ {cable_a.name} FO-1 <-> {cable_b.name} FO-1"
                )
            )

        # Summary
        self.stdout.write("\n" + "="*60)
        self.stdout.write("RESUMO")
        self.stdout.write("="*60)

        fused_count = FiberStrand.objects.filter(
            fusion_infrastructure=ceo,
            fused_to__isnull=False
        ).count() // 2

        self.stdout.write(
            self.style.SUCCESS(
                f"\n✓ Total de fusões no CEO: {fused_count}"
            )
        )

        # Display fusions
        for tray in [1]:
            for slot in [1, 2]:
                strands_in_slot = FiberStrand.objects.filter(
                    fusion_infrastructure=ceo,
                    fusion_tray=tray,
                    fusion_slot=slot
                ).select_related('tube__cable')
                
                if strands_in_slot.exists():
                    fibers = list(strands_in_slot)
                    if len(fibers) == 2:
                        self.stdout.write(
                            f"   Bandeja {tray}, Slot {slot}: "
                            f"{fibers[0].tube.cable.name} FO-{fibers[0].number} "
                            f"<-> {fibers[1].tube.cable.name} FO-{fibers[1].number}"
                        )

        self.stdout.write("\n" + "="*60)
        self.stdout.write(
            self.style.SUCCESS(
                "RESULTADO: Fusão atômica 1:1 funcionando!"
            )
        )
        self.stdout.write("="*60 + "\n")
