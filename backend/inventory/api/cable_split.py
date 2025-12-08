"""API endpoint for permanent cable splitting at CEO points."""

from decimal import Decimal
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from django.db import transaction
from django.contrib.gis.geos import LineString

from inventory.models import (
    FiberCable,
    FiberInfrastructure,
    InfrastructureCableAttachment,
    BufferTube,
    FiberStrand,
)


class CableSplitViewSet(viewsets.ViewSet):
    """
    ViewSet for permanent cable splitting operations.
    """

    @action(detail=False, methods=['post'])
    def split_at_ceo(self, request):
        """
        Split a cable permanently into two cables at a CEO point.
        
        Request:
        {
            "cable_id": 123,
            "ceo_id": 456,
            "split_point": {"lat": -15.123, "lng": -47.456}
        }
        
        This will:
        1. Create Cable A-CEO (site_a → CEO)
        2. Create Cable CEO-B (CEO → site_b)
        3. Copy all tubes/strands to both cables
        4. Create attachments for both cables
        5. Delete original cable
        """
        cable_id = request.data.get('cable_id')
        ceo_id = request.data.get('ceo_id')
        split_point = request.data.get('split_point')

        if not cable_id or not ceo_id or not split_point:
            return Response(
                {"error": "cable_id, ceo_id e split_point são obrigatórios"},
                status=status.HTTP_400_BAD_REQUEST
            )

        cable = get_object_or_404(FiberCable, id=cable_id)
        ceo = get_object_or_404(
            FiberInfrastructure,
            id=ceo_id,
            type='splice_box',
        )

        if cable.notes and '[ROMPIDO]' in cable.notes:
            return self._handle_already_split(cable=cable, ceo=ceo)

        if not cable.path:
            return Response(
                {"error": "Cabo deve ter path (geometria) configurado"},
                status=status.HTTP_400_BAD_REQUEST
            )

        with transaction.atomic():
            # Converter path original para lista de coordenadas
            original_coords = list(cable.path.coords)
            split_lat = split_point['lat']
            split_lng = split_point['lng']
            
            # Encontrar índice mais próximo do ponto de split
            split_idx = self._find_split_index(
                original_coords,
                split_lat,
                split_lng,
            )
            
            # Dividir path em dois segmentos
            path_a_coords = (
                original_coords[: split_idx + 1]
                + [(split_lng, split_lat)]
            )
            path_b_coords = (
                [(split_lng, split_lat)]
                + original_coords[split_idx + 1:]
            )
            
            # Criar LineStrings
            path_a = LineString(path_a_coords, srid=4326)
            path_b = LineString(path_b_coords, srid=4326)
            
            # Calcular comprimentos (distância geodésica)
            # Conversão simples de graus para km (aproximação local)
            length_a_km = Decimal(str(round(path_a.length * 111, 3)))
            length_b_km = Decimal(str(round(path_b.length * 111, 3)))
            
            # Gerar nomes únicos para os novos segmentos
            cable_a_name = self._generate_segment_name(cable.name, 'A')
            cable_b_name = self._generate_segment_name(cable.name, 'B')

            # Criar Cabo A-CEO
            cable_a = FiberCable.objects.create(
                name=cable_a_name,
                profile=cable.profile,
                site_a=cable.site_a,
                site_b=None,  # Termina na CEO
                origin_port=cable.origin_port,
                destination_port=None,
                path=path_a,
                length_km=length_a_km,
                status=cable.status,
                notes=f"Cabo partido de {cable.name} (segmento A-CEO)"
            )
            
            # Criar Cabo CEO-B
            cable_b = FiberCable.objects.create(
                name=cable_b_name,
                profile=cable.profile,
                site_a=None,  # Começa na CEO
                site_b=cable.site_b,
                origin_port=None,
                destination_port=cable.destination_port,
                path=path_b,
                length_km=length_b_km,
                status=cable.status,
                notes=f"Cabo partido de {cable.name} (segmento CEO-B)"
            )
            
            # Copiar tubos e fibras para AMBOS os cabos
            map_a, map_b = self._duplicate_cable_structure(
                cable,
                cable_a,
                cable_b,
            )
            
            # Criar attachments para ambos os segmentos na CEO do split
            InfrastructureCableAttachment.objects.create(
                infrastructure=ceo,
                cable=cable_a,
                port_type='oval',
                is_pass_through=False  # Segmento A termina aqui
            )
            
            InfrastructureCableAttachment.objects.create(
                infrastructure=ceo,
                cable=cable_b,
                port_type='oval',
                is_pass_through=False  # Segmento B termina aqui
            )

            moved_to_a, moved_to_b = self._reassign_existing_attachments(
                original_cable=cable,
                split_ceo=ceo,
                cable_a=cable_a,
                cable_b=cable_b,
            )

            migrated_a, migrated_b = self._migrate_existing_fusions(
                original_cable=cable,
                split_ceo=ceo,
                cable_a=cable_a,
                cable_b=cable_b,
                strand_map_a=map_a,
                strand_map_b=map_b,
            )
            
            # Marcar cabo original como ROMPIDO
            # (não deve mais aparecer em CEOs)
            cable.notes = (
                f"[ROMPIDO] Cabo partido em {ceo.name}. "
                f"Extremidades: {cable_a.name} (ID {cable_a.id}) e "
                f"{cable_b.name} (ID {cable_b.id})"
            )
            cable.save(update_fields=['notes'])
            
        return Response({
            "status": "success",
            "message": (
                f"Cabo {cable.name} partido em 2 extremidades "
                f"na CEO {ceo.name}. Cabo original mantido."
            ),
            "original_cable": {
                "id": cable.id,
                "name": cable.name,
                "total_length_km": (
                    float(cable.length_km) if cable.length_km else 0
                ),
            },
            "cable_a": {
                "id": cable_a.id,
                "name": cable_a.name,
                "length_km": float(cable_a.length_km),
                "description": "Extremidade A (início → CEO)",
                "attachments_migrated": moved_to_a,
                "fusions_migrated": migrated_a,
            },
            "cable_b": {
                "id": cable_b.id,
                "name": cable_b.name,
                "length_km": float(cable_b.length_km),
                "description": "Extremidade B (CEO → fim)",
                "attachments_migrated": moved_to_b,
                "fusions_migrated": migrated_b,
            },
        }, status=status.HTTP_201_CREATED)

    def _handle_already_split(
        self,
        *,
        cable: FiberCable,
        ceo: FiberInfrastructure,
    ) -> Response:
        """Reutiliza extremidades quando o cabo já estava partido."""
        cable_a, cable_b = self._find_existing_segments(
            original_cable=cable,
            split_ceo=ceo,
        )

        if not cable_a or not cable_b:
            return Response(
                {
                    "error": (
                        "Este cabo já foi partido anteriormente, mas as "
                        "extremidades não foram localizadas automaticamente."
                    ),
                    "original_cable_id": cable.id,
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        self._ensure_ceo_attachment(ceo=ceo, cable=cable_a)
        self._ensure_ceo_attachment(ceo=ceo, cable=cable_b)

        moved_to_a, moved_to_b = self._reassign_existing_attachments(
            original_cable=cable,
            split_ceo=ceo,
            cable_a=cable_a,
            cable_b=cable_b,
        )

        return Response(
            {
                "status": "noop",
                "message": (
                    "Cabo já estava partido. Extremidades existentes foram "
                    "reutilizadas e pendências de anexos saneadas."
                ),
                "original_cable": {
                    "id": cable.id,
                    "name": cable.name,
                },
                "cable_a": {
                    "id": cable_a.id,
                    "name": cable_a.name,
                    "attachments_migrated": moved_to_a,
                },
                "cable_b": {
                    "id": cable_b.id,
                    "name": cable_b.name,
                    "attachments_migrated": moved_to_b,
                },
            },
            status=status.HTTP_200_OK,
        )

    def _generate_segment_name(self, base_name: str, suffix: str) -> str:
        """Gera um nome único para a extremidade (evita conflitos)."""
        candidate = f"{base_name}-{suffix}"
        counter = 2

        while FiberCable.objects.filter(name=candidate).exists():
            candidate = f"{base_name}-{suffix}{counter}"
            counter += 1

        return candidate

    def _find_split_index(self, coords, target_lat, target_lng):
        """Encontra o índice da coordenada mais próxima do ponto de split."""
        min_dist = float('inf')
        min_idx = 0
        
        for i, (lng, lat) in enumerate(coords):
            dist = ((lat - target_lat) ** 2 + (lng - target_lng) ** 2) ** 0.5
            if dist < min_dist:
                min_dist = dist
                min_idx = i
        
        return min_idx

    def _duplicate_cable_structure(self, original_cable, cable_a, cable_b):
        """Copia tubos e fibras e retorna mapas de correspondência."""
        tubes = BufferTube.objects.filter(
            cable=original_cable
        ).order_by('number')

        strand_map_a: dict[int, FiberStrand] = {}
        strand_map_b: dict[int, FiberStrand] = {}

        for tube in tubes:
            tube_a = BufferTube.objects.create(
                cable=cable_a,
                number=tube.number,
                color=tube.color,
                color_hex=tube.color_hex,
            )

            tube_b = BufferTube.objects.create(
                cable=cable_b,
                number=tube.number,
                color=tube.color,
                color_hex=tube.color_hex,
            )

            strands = FiberStrand.objects.filter(tube=tube).order_by('number')
            for strand in strands:
                strand_a = FiberStrand.objects.create(
                    tube=tube_a,
                    number=strand.number,
                    absolute_number=strand.absolute_number,
                    color=strand.color,
                    color_hex=strand.color_hex,
                    fused_to=None,
                    connected_device_port=None,
                    status=strand.status,
                )

                strand_b = FiberStrand.objects.create(
                    tube=tube_b,
                    number=strand.number,
                    absolute_number=strand.absolute_number,
                    color=strand.color,
                    color_hex=strand.color_hex,
                    fused_to=None,
                    connected_device_port=None,
                    status=strand.status,
                )

                strand_map_a[strand.id] = strand_a
                strand_map_b[strand.id] = strand_b

        return strand_map_a, strand_map_b

    def _reassign_existing_attachments(
        self,
        *,
        original_cable: FiberCable,
        split_ceo: FiberInfrastructure,
        cable_a: FiberCable,
        cable_b: FiberCable,
    ) -> tuple[int, int]:
        """
        Move attachments do cabo original para as novas extremidades.

        Mantém o mesmo tipo de porta e flag de pass-through, decidindo
        o lado baseado na distância da infraestrutura em relação à CEO
        onde ocorreu o rompimento.
        """
        attachments = list(
            InfrastructureCableAttachment.objects.filter(
                cable=original_cable
            ).select_related('infrastructure')
        )

        if not attachments:
            return 0, 0

        ceo_distance = split_ceo.distance_from_origin or 0
        moved_to_a = 0
        moved_to_b = 0

        for attachment in attachments:
            infra = attachment.infrastructure

            # Remover vínculo pass-through do cabo original nesta CEO
            if infra.id == split_ceo.id:
                attachment.delete()
                continue

            infra_distance = infra.distance_from_origin or 0
            target_cable = (
                cable_a if infra_distance <= ceo_distance else cable_b
            )

            InfrastructureCableAttachment.objects.update_or_create(
                infrastructure=infra,
                cable=target_cable,
                port_type=attachment.port_type,
                defaults={
                    'is_pass_through': attachment.is_pass_through
                }
            )

            if target_cable == cable_a:
                moved_to_a += 1
            else:
                moved_to_b += 1

            attachment.delete()

        return moved_to_a, moved_to_b

    def _migrate_existing_fusions(
        self,
        *,
        original_cable: FiberCable,
        split_ceo: FiberInfrastructure,
        cable_a: FiberCable,
        cable_b: FiberCable,
        strand_map_a: dict[int, FiberStrand],
        strand_map_b: dict[int, FiberStrand],
    ) -> tuple[int, int]:
        """Realoca fusões das fibras do cabo original nos novos segmentos."""

        ceo_distance = split_ceo.distance_from_origin or 0
        migrated_a = 0
        migrated_b = 0

        strands = FiberStrand.objects.filter(
            tube__cable=original_cable,
            fusion_infrastructure__isnull=False,
        ).select_related(
            'fusion_infrastructure',
            'fused_to',
            'fused_to__fusion_infrastructure',
            'fused_to__tube__cable',
            'tube',
        )

        processed: set[int] = set()

        for strand in strands:
            if strand.id in processed:
                continue

            infra = strand.fusion_infrastructure
            if not infra:
                continue

            target_map = (
                strand_map_a
                if (infra.distance_from_origin or 0) <= ceo_distance
                else strand_map_b
            )
            target_strand = target_map.get(strand.id)
            if not target_strand:
                continue

            partner = strand.fused_to
            target_strand.fusion_infrastructure = infra
            target_strand.fusion_tray = strand.fusion_tray
            target_strand.fusion_slot = strand.fusion_slot

            if partner and partner.tube.cable_id == original_cable.id:
                partner_distance = (
                    partner.fusion_infrastructure.distance_from_origin
                    if partner.fusion_infrastructure
                    else 0
                )
                partner_map = (
                    strand_map_a
                    if partner_distance <= ceo_distance
                    else strand_map_b
                )
                partner_target = partner_map.get(partner.id)
                if partner_target:
                    target_strand.fused_to = partner_target
                    partner_target.fused_to = target_strand
                    partner_target.fusion_infrastructure = (
                        partner.fusion_infrastructure
                    )
                    partner_target.fusion_tray = partner.fusion_tray
                    partner_target.fusion_slot = partner.fusion_slot
                    partner_target.save(
                        update_fields=[
                            'fused_to',
                            'fusion_infrastructure',
                            'fusion_tray',
                            'fusion_slot',
                        ]
                    )
                    partner.fused_to = None
                    partner.fusion_infrastructure = None
                    partner.fusion_tray = None
                    partner.fusion_slot = None
                    partner.save(
                        update_fields=[
                            'fused_to',
                            'fusion_infrastructure',
                            'fusion_tray',
                            'fusion_slot',
                        ]
                    )
                    processed.add(partner.id)
                else:
                    target_strand.fused_to = None
            elif partner:
                target_strand.fused_to = partner
                partner.fused_to = target_strand
                partner.save(update_fields=['fused_to'])
            else:
                target_strand.fused_to = None

            target_strand.save(
                update_fields=[
                    'fused_to',
                    'fusion_infrastructure',
                    'fusion_tray',
                    'fusion_slot',
                ]
            )

            if target_map is strand_map_a:
                migrated_a += 1
            else:
                migrated_b += 1

            strand.fused_to = None
            strand.fusion_infrastructure = None
            strand.fusion_tray = None
            strand.fusion_slot = None
            strand.save(
                update_fields=[
                    'fused_to',
                    'fusion_infrastructure',
                    'fusion_tray',
                    'fusion_slot',
                ]
            )

            processed.add(strand.id)

        return migrated_a, migrated_b

    def _find_existing_segments(
        self,
        *,
        original_cable: FiberCable,
        split_ceo: FiberInfrastructure,
    ) -> tuple[FiberCable | None, FiberCable | None]:
        """Localiza segmentos já criados para um cabo previamente partido."""
        candidates = list(
            FiberCable.objects.filter(
                notes__icontains=f"Cabo partido de {original_cable.name}"
            )
        )

        cable_a = next((c for c in candidates if c.site_b_id is None), None)
        cable_b = next((c for c in candidates if c.site_a_id is None), None)

        if not cable_a:
            cable_a = next(
                (
                    c for c in candidates
                    if c.name.startswith(f"{original_cable.name}-A")
                ),
                None,
            )

        if not cable_b:
            cable_b = next(
                (
                    c for c in candidates
                    if c.name.startswith(f"{original_cable.name}-B")
                ),
                None,
            )

        return cable_a, cable_b

    def _ensure_ceo_attachment(
        self,
        *,
        ceo: FiberInfrastructure,
        cable: FiberCable,
    ) -> None:
        """Garante que a CEO possua o vínculo com o cabo informado."""
        if not cable:
            return

        InfrastructureCableAttachment.objects.update_or_create(
            infrastructure=ceo,
            cable=cable,
            defaults={
                'port_type': 'oval',
                'is_pass_through': False,
            },
        )
