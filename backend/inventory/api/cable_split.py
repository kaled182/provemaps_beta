"""API endpoint for permanent cable splitting at CEO points."""

from decimal import Decimal
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from django.db import transaction
from django.db.models import Q
from django.contrib.gis.geos import LineString

from inventory.models import (
    FiberCable,
    FiberInfrastructure,
    InfrastructureCableAttachment,
    BufferTube,
    FiberStrand,
    FiberFusion,
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
        import logging
        logger = logging.getLogger(__name__)
        logger.info("=" * 80)
        logger.info("[SPLIT API] Recebendo requisição de split...")
        logger.info(f"[SPLIT API] Request data: {request.data}")
        
        cable_id = request.data.get('cable_id')
        ceo_id = request.data.get('ceo_id')
        split_point = request.data.get('split_point')
        
        logger.info(f"[SPLIT API] cable_id={cable_id}, ceo_id={ceo_id}, split_point={split_point}")

        if not cable_id or not ceo_id or not split_point:
            logger.error("[SPLIT API] Parâmetros faltando!")
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
        
        logger.info(f"[SPLIT API] Cabo encontrado: {cable.name} (ID {cable.id})")
        logger.info(f"[SPLIT API] CEO encontrada: {ceo.name} (ID {ceo.id})")

        if cable.notes and '[ROMPIDO]' in cable.notes:
            logger.info("[SPLIT API] Cabo já está rompido, reutilizando segmentos...")
            return self._handle_already_split(cable=cable, ceo=ceo)

        if not cable.path:
            logger.error("[SPLIT API] Cabo sem path!")
            return Response(
                {"error": "Cabo deve ter path (geometria) configurado"},
                status=status.HTTP_400_BAD_REQUEST
            )

        with transaction.atomic():
            logger.info("[SPLIT API] Iniciando transação...")
            
            # Converter path original para lista de coordenadas
            original_coords = list(cable.path.coords)
            split_lat = split_point['lat']
            split_lng = split_point['lng']
            
            logger.info(f"[SPLIT API] Path original tem {len(original_coords)} coordenadas")
            logger.info(f"[SPLIT API] Ponto de split: lat={split_lat}, lng={split_lng}")
            
            # Encontrar índice mais próximo do ponto de split
            split_idx = self._find_split_index(
                original_coords,
                split_lat,
                split_lng,
            )
            
            logger.info(f"[SPLIT API] Índice de split encontrado: {split_idx}")
            
            # Dividir path em dois segmentos
            path_a_coords = (
                original_coords[: split_idx + 1]
                + [(split_lng, split_lat)]
            )
            path_b_coords = (
                [(split_lng, split_lat)]
                + original_coords[split_idx + 1:]
            )
            
            logger.info(f"[SPLIT API] Path A: {len(path_a_coords)} coords, Path B: {len(path_b_coords)} coords")
            
            # Criar LineStrings
            path_a = LineString(path_a_coords, srid=4326)
            path_b = LineString(path_b_coords, srid=4326)
            
            # Calcular comprimentos (distância geodésica)
            # Conversão simples de graus para km (aproximação local)
            length_a_km = Decimal(str(round(path_a.length * 111, 3)))
            length_b_km = Decimal(str(round(path_b.length * 111, 3)))
            
            logger.info(f"[SPLIT API] Comprimento A: {length_a_km} km, B: {length_b_km} km")
            
            # Gerar nomes únicos para os novos segmentos
            cable_a_name = self._generate_segment_name(cable.name, 'A')
            cable_b_name = self._generate_segment_name(cable.name, 'B')
            
            logger.info(f"[SPLIT API] Nomes gerados: {cable_a_name}, {cable_b_name}")

            # Criar Cabo A-CEO
            cable_a = FiberCable.objects.create(
                name=cable_a_name,
                profile=cable.profile,
                parent_cable=cable,  # Mark as segment
                site_a=cable.site_a,
                site_b=None,  # Termina na CEO
                origin_port=cable.origin_port,
                destination_port=None,
                path=path_a,
                length_km=length_a_km,
                status=cable.status,
                notes=f"Cabo partido de {cable.name} (segmento A-CEO)"
            )
            
            logger.info(f"[SPLIT API] Cabo A criado: {cable_a.name} (ID {cable_a.id})")
            
            # Criar Cabo CEO-B
            cable_b = FiberCable.objects.create(
                name=cable_b_name,
                profile=cable.profile,
                parent_cable=cable,  # Mark as segment
                site_a=None,  # Começa na CEO
                site_b=cable.site_b,
                origin_port=None,
                destination_port=cable.destination_port,
                path=path_b,
                length_km=length_b_km,
                status=cable.status,
                notes=f"Cabo partido de {cable.name} (segmento CEO-B)"
            )
            
            logger.info(f"[SPLIT API] Cabo B criado: {cable_b.name} (ID {cable_b.id})")
            
            # Copiar tubos e fibras para AMBOS os cabos
            logger.info("[SPLIT API] Duplicando estrutura de tubos e fibras...")
            map_a, map_b = self._duplicate_cable_structure(
                cable,
                cable_a,
                cable_b,
            )
            
            logger.info(f"[SPLIT API] Estrutura duplicada. Map A: {len(map_a)} fibras, Map B: {len(map_b)} fibras")
            
            # Criar attachments para ambos os segmentos na CEO do split
            logger.info("[SPLIT API] Criando attachments...")
            InfrastructureCableAttachment.objects.create(
                infrastructure=ceo,
                cable=cable_a,
                port_type='oval',
                is_pass_through=False  # Segmento A termina aqui
            )
            
            logger.info(f"[SPLIT API] Attachment criado: {cable_a.name} → {ceo.name}")
            
            InfrastructureCableAttachment.objects.create(
                infrastructure=ceo,
                cable=cable_b,
                port_type='oval',
                is_pass_through=False  # Segmento B termina aqui
            )
            
            logger.info(f"[SPLIT API] Attachment criado: {cable_b.name} → {ceo.name}")

            logger.info("[SPLIT API] Reatribuindo attachments existentes...")
            moved_to_a, moved_to_b = self._reassign_existing_attachments(
                original_cable=cable,
                split_ceo=ceo,
                cable_a=cable_a,
                cable_b=cable_b,
            )
            
            logger.info(f"[SPLIT API] Attachments reatribuídos: A={moved_to_a}, B={moved_to_b}")

            logger.info("[SPLIT API] Migrando fusões existentes...")
            migrated_a, migrated_b = self._migrate_existing_fusions(
                original_cable=cable,
                split_ceo=ceo,
                cable_a=cable_a,
                cable_b=cable_b,
                strand_map_a=map_a,
                strand_map_b=map_b,
            )
            
            logger.info(f"[SPLIT API] Fusões migradas: A={migrated_a}, B={migrated_b}")
            
            # Marcar cabo original como ROMPIDO
            # (não deve mais aparecer em CEOs)
            cable.notes = (
                f"[ROMPIDO] Cabo partido em {ceo.name}. "
                f"Extremidades: {cable_a.name} (ID {cable_a.id}) e "
                f"{cable_b.name} (ID {cable_b.id})"
            )
            cable.save(update_fields=['notes'])
            
            logger.info("[SPLIT API] Cabo original marcado como [ROMPIDO]")
            logger.info("[SPLIT API] Split concluído com sucesso!")
            logger.info("=" * 80)
            
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
        import logging
        logger = logging.getLogger(__name__)
        
        logger.info(f"[_duplicate_cable_structure] Iniciando duplicação de {original_cable.name}")
        
        tubes = BufferTube.objects.filter(
            cable=original_cable
        ).order_by('number')
        
        logger.info(f"[_duplicate_cable_structure] Encontrados {tubes.count()} tubos no cabo original")

        strand_map_a: dict[int, FiberStrand] = {}
        strand_map_b: dict[int, FiberStrand] = {}

        for tube in tubes:
            logger.info(f"[_duplicate_cable_structure] Duplicando tubo {tube.number} ({tube.color})")
            
            tube_a = BufferTube.objects.create(
                cable=cable_a,
                number=tube.number,
                color=tube.color,
                color_hex=tube.color_hex,
            )
            
            logger.info(f"[_duplicate_cable_structure] Tubo A criado: {tube_a.id}")

            tube_b = BufferTube.objects.create(
                cable=cable_b,
                number=tube.number,
                color=tube.color,
                color_hex=tube.color_hex,
            )
            
            logger.info(f"[_duplicate_cable_structure] Tubo B criado: {tube_b.id}")

            strands = FiberStrand.objects.filter(tube=tube).order_by('number')
            logger.info(f"[_duplicate_cable_structure] Tubo {tube.number} tem {strands.count()} fibras")
            
            for strand in strands:
                strand_a = FiberStrand.objects.create(
                    tube=tube_a,
                    number=strand.number,
                    absolute_number=strand.absolute_number,
                    color=strand.color,
                    color_hex=strand.color_hex,
                    connected_device_port=None,
                    status=strand.status,
                )

                strand_b = FiberStrand.objects.create(
                    tube=tube_b,
                    number=strand.number,
                    absolute_number=strand.absolute_number,
                    color=strand.color,
                    color_hex=strand.color_hex,
                    connected_device_port=None,
                    status=strand.status,
                )

                strand_map_a[strand.id] = strand_a
                strand_map_b[strand.id] = strand_b
                
                logger.info(
                    f"[_duplicate_cable_structure] Fibra {strand.number}: "
                    f"Original ID={strand.id} → A ID={strand_a.id}, B ID={strand_b.id}"
                )
        
        logger.info(f"[_duplicate_cable_structure] Duplicação concluída. Total: {len(strand_map_a)} fibras/cabo")

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

        fusions = (
            FiberFusion.objects.filter(
                Q(fiber_a__tube__cable=original_cable)
                | Q(fiber_b__tube__cable=original_cable)
            )
            .select_related(
                'infrastructure',
                'fiber_a__tube__cable',
                'fiber_b__tube__cable',
            )
        )

        legacy_strands: dict[int, FiberStrand] = {}

        for fusion in fusions:
            infra = fusion.infrastructure
            if not infra:
                continue

            infra_distance = infra.distance_from_origin or 0
            target_map = (
                strand_map_a
                if infra_distance <= ceo_distance
                else strand_map_b
            )
            map_token = 'A' if target_map is strand_map_a else 'B'

            replacements: dict[str, FiberStrand] = {}
            migrated_maps: set[str] = set()

            original_fiber_a = fusion.fiber_a
            original_fiber_b = fusion.fiber_b

            if original_fiber_a.tube.cable_id == original_cable.id:
                replacement_a = target_map.get(original_fiber_a.id)
                if replacement_a:
                    replacements['fiber_a'] = replacement_a
                    migrated_maps.add(map_token)
                    legacy_strands[original_fiber_a.id] = original_fiber_a

            if original_fiber_b.tube.cable_id == original_cable.id:
                replacement_b = target_map.get(original_fiber_b.id)
                if replacement_b:
                    replacements['fiber_b'] = replacement_b
                    migrated_maps.add(map_token)
                    legacy_strands[original_fiber_b.id] = original_fiber_b

            if not replacements:
                continue

            update_fields: list[str] = []
            for field_name, strand in replacements.items():
                setattr(fusion, field_name, strand)
                update_fields.append(field_name)

            fusion.save(update_fields=update_fields)

            if 'A' in migrated_maps:
                migrated_a += 1
            if 'B' in migrated_maps:
                migrated_b += 1

        for strand in legacy_strands.values():
            if strand.status != FiberStrand.STATUS_DARK:
                strand.status = FiberStrand.STATUS_DARK
                strand.save(update_fields=['status'])

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
