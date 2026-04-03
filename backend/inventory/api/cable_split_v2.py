"""
Versão 2.0 do Cable Split usando CableSegments corretamente.

DIFERENÇAS DA V1:
- NÃO cria novos FiberCables (cable_a, cable_b)
- USA auto_segment_cable_at_ceo() do cable_segments service
- CRIA segmento BROKEN para representar o corte físico
- MANTÉM o FiberCable original intacto
"""
import logging
from decimal import Decimal
from typing import TypedDict

from django.contrib.gis.geos import LineString
from django.db import transaction
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from inventory.models import FiberCable, FiberInfrastructure, CableSegment, InfrastructureCableAttachment
from inventory.services.cable_segments import auto_segment_cable_at_ceo

logger = logging.getLogger(__name__)


class SplitPoint(TypedDict):
    lat: float
    lng: float


class CableSplitV2View(APIView):
    """
    API View para split de cabos usando sistema de CableSegments.
    
    Endpoint: POST /api/v1/inventory/cables/<id>/split-at-ceo-v2/
    
    Payload:
        {
            "ceo_id": 123
        }
    """

    def post(self, request, pk):
        """
        Divide cabo na CEO usando CableSegments ao invés de criar novos cabos.
        
        Fluxo:
        1. Validar cabo + CEO
        2. Calcular distância da CEO ao longo do path do cabo
        3. Usar auto_segment_cable_at_ceo() para criar seg_before e seg_after
        4. Criar CableSegment.STATUS_BROKEN virtual representando o corte
        5. Criar attachment do cabo original na CEO
        6. Retornar estrutura de segmentos
        """
        logger.info("=" * 80)
        logger.info("[SPLIT V2] Iniciando split usando CableSegments...")
        
        ceo_id = request.data.get('ceo_id')
        
        if not ceo_id:
            return Response(
                {"error": "ceo_id é obrigatório"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        cable = get_object_or_404(FiberCable, id=pk)
        ceo = get_object_or_404(FiberInfrastructure, id=ceo_id, type='splice_box')
        
        logger.info(f"[SPLIT V2] Cabo: {cable.name} (ID {cable.id})")
        logger.info(f"[SPLIT V2] CEO: {ceo.name} (ID {ceo.id})")
        
        if not cable.path:
            return Response(
                {"error": "Cabo deve ter path (geometria) configurado"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        with transaction.atomic():
            # 1. Calcular distância da CEO ao longo do cabo
            # Usar as coordenadas da própria CEO (já está anexada ao cabo)
            if not ceo.location:
                return Response(
                    {"error": f"CEO {ceo.name} não tem localização definida"},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            ceo_lng, ceo_lat = ceo.location.coords
            distance_km = self._calculate_ceo_distance_along_cable(
                cable=cable,
                ceo_lat=ceo_lat,
                ceo_lng=ceo_lng
            )
            
            logger.info(f"[SPLIT V2] CEO está a {distance_km:.3f}km do início do cabo")
            
            # Converter para metros para uso pelo service
            distance_meters = distance_km * 1000
            
            # 2. Criar ou atualizar segmentos usando service layer
            seg_before, seg_after = auto_segment_cable_at_ceo(
                cable=cable,
                ceo=ceo,
                distance_meters=distance_meters
            )
            
            logger.info(f"[SPLIT V2] Segmentos criados:")
            logger.info(f"  - {seg_before.name}: {seg_before.length_meters}m")
            logger.info(f"  - {seg_after.name}: {seg_after.length_meters}m")
            
            # 3. CRÍTICO: Criar segmento BROKEN virtual representando o corte físico
            # Precisamos renumerar seg_after primeiro para abrir espaço
            original_after_num = seg_after.segment_number
            new_broken_num = original_after_num  # BROKEN fica no lugar do seg_after
            new_after_num = original_after_num + 1  # seg_after vai para o próximo
            
            # Renumerar segmentos posteriores (se houver) para evitar conflito
            from django.db import models
            CableSegment.objects.filter(
                cable=cable,
                segment_number__gte=original_after_num
            ).update(segment_number=models.F('segment_number') + 1)
            
            # Recarregar seg_after após renumeração
            seg_after.refresh_from_db()
            
            # Agora criar o BROKEN no número original do seg_after
            broken_segment = CableSegment.objects.create(
                cable=cable,
                segment_number=new_broken_num,
                name=f"{cable.name}-BREAK-{ceo.name}",
                start_infrastructure=ceo,
                end_infrastructure=ceo,  # CEO é tanto início quanto fim (ponto de corte)
                length_meters=0,  # Comprimento zero (é um ponto de descontinuidade)
                status=CableSegment.STATUS_BROKEN,  # CRUCIAL: marca como BROKEN
                has_loose_ends=True  # PONTAS SOLTAS: aguardando conexão manual
            )
            
            logger.info(f"[SPLIT V2] Segmento BROKEN criado: {broken_segment.name}")
            logger.info(f"[SPLIT V2] Status: {broken_segment.status}, has_loose_ends: {broken_segment.has_loose_ends}")
            
            # 4. NÃO criar attachment automaticamente - deixar pontas soltas!
            # O usuário deve arrastar manualmente cada ponta para a CEO
            # REMOVIDO: InfrastructureCableAttachment.objects.get_or_create(...)
            
            logger.info("[SPLIT V2] PONTAS SOLTAS: Segmentos aguardando conexão manual")
            logger.info(f"[SPLIT V2] Ponta A (Seg {seg_before.segment_number}): {seg_before.name}")
            logger.info(f"[SPLIT V2] Ponta B (Seg {seg_after.segment_number}): {seg_after.name}")
            
            # 5. Marcar cabo original com nota sobre o split
            cable.notes = (
                f"{cable.notes}\n" if cable.notes else ""
            ) + f"[SPLIT] Cabo partido em {ceo.name} (CEO ID {ceo.id}). Segmentos: {seg_before.name}, BREAK, {seg_after.name}"
            cable.save(update_fields=['notes'])
            
            logger.info("[SPLIT V2] Split concluído com sucesso!")
            logger.info(f"[SPLIT V2] Estrutura: {seg_before.name} → BREAK → {seg_after.name}")
            logger.info("=" * 80)
        
        return Response({
            "status": "success",
            "message": f"Cabo {cable.name} partido. Arraste as pontas para conectá-las à CEO.",
            "cable": {
                "id": cable.id,
                "name": cable.name,
                "total_length_km": float(cable.length_km) if cable.length_km else 0,
            },
            "segments": {
                "before": {
                    "id": seg_before.id,
                    "name": seg_before.name,
                    "length_m": seg_before.length_meters,
                    "status": seg_before.status,
                    "segment_number": seg_before.segment_number,
                },
                "broken": {
                    "id": broken_segment.id,
                    "name": broken_segment.name,
                    "length_m": broken_segment.length_meters,
                    "status": broken_segment.status,
                    "segment_number": broken_segment.segment_number,
                },
                "after": {
                    "id": seg_after.id,
                    "name": seg_after.name,
                    "length_m": seg_after.length_meters,
                    "status": seg_after.status,
                    "segment_number": seg_after.segment_number,
                },
            },
            "ceo": {
                "id": ceo.id,
                "name": ceo.name,
            },
            # NOVO: Informações para o frontend renderizar pontas soltas
            "loose_ends": {
                "end_a": {
                    "segment_id": seg_before.id,
                    "segment_number": seg_before.segment_number,
                    "is_start": False,  # Ponta FIM do seg_before
                    "location": {
                        "lat": ceo.location.y,
                        "lng": ceo.location.x
                    } if ceo.location else None,
                    "requires_attachment": True
                },
                "end_b": {
                    "segment_id": seg_after.id,
                    "segment_number": seg_after.segment_number,
                    "is_start": True,  # Ponta INÍCIO do seg_after  
                    "location": {
                        "lat": ceo.location.y,
                        "lng": ceo.location.x
                    } if ceo.location else None,
                    "requires_attachment": True
                }
            }
        }, status=status.HTTP_201_CREATED)
    
    def _calculate_ceo_distance_along_cable(
        self,
        cable: FiberCable,
        ceo_lat: float,
        ceo_lng: float
    ) -> float:
        """
        Calcula distância da CEO ao longo do path do cabo (em km).
        
        Retorna a distância acumulada até o ponto mais próximo da CEO.
        """
        from django.contrib.gis.geos import Point
        
        coords = list(cable.path.coords)
        ceo_point = Point(ceo_lng, ceo_lat, srid=4326)
        
        # Encontrar índice da coordenada mais próxima
        min_dist = float('inf')
        min_idx = 0
        
        for i, (lng, lat) in enumerate(coords):
            point = Point(lng, lat, srid=4326)
            dist = ceo_point.distance(point)
            if dist < min_dist:
                min_dist = dist
                min_idx = i
        
        # Calcular distância acumulada até este ponto
        accumulated_km = 0.0
        for i in range(min_idx):
            p1 = Point(coords[i][0], coords[i][1], srid=4326)
            p2 = Point(coords[i+1][0], coords[i+1][1], srid=4326)
            # Aproximação: 1 grau ~ 111km
            accumulated_km += p1.distance(p2) * 111
        
        return accumulated_km
