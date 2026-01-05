"""
API endpoint para listar segmentos com pontas soltas.

Endpoint: GET /api/v1/inventory/segments/loose-ends/?cable_id=123
"""
import logging

from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from inventory.models import CableSegment

logger = logging.getLogger(__name__)


class ListLooseEndsView(APIView):
    """
    Lista todos os segmentos com pontas soltas (has_loose_ends=True).
    Pode filtrar por cable_id.
    """

    def get(self, request):
        cable_id = request.query_params.get('cable_id')
        
        # Query base: segmentos com pontas soltas
        queryset = CableSegment.objects.filter(
            has_loose_ends=True,
            status=CableSegment.STATUS_BROKEN
        ).select_related(
            'cable',
            'start_infrastructure',
            'end_infrastructure'
        )
        
        # Filtrar por cabo se especificado
        if cable_id:
            queryset = queryset.filter(cable_id=cable_id)
        
        logger.info(f"[LIST_LOOSE_ENDS] Encontrados {queryset.count()} segmentos com pontas soltas" +
                   (f" no cabo {cable_id}" if cable_id else ""))
        
        result = []
        for segment in queryset:
            # Calcular coordenadas das pontas (início e fim do segmento rompido)
            start_coords = None
            end_coords = None
            
            if segment.start_infrastructure and segment.start_infrastructure.location:
                start_coords = {
                    "lat": segment.start_infrastructure.location.y,
                    "lng": segment.start_infrastructure.location.x
                }
            
            if segment.end_infrastructure and segment.end_infrastructure.location:
                end_coords = {
                    "lat": segment.end_infrastructure.location.y,
                    "lng": segment.end_infrastructure.location.x
                }
            
            # Se não tem infraestrutura, usar extremidades do path do cabo
            if not start_coords or not end_coords:
                cable_path = segment.cable.path
                if cable_path and hasattr(cable_path, 'coords') and len(cable_path.coords) >= 2:
                    if not start_coords:
                        first_point = cable_path.coords[0]
                        start_coords = {"lat": first_point[1], "lng": first_point[0]}
                    if not end_coords:
                        last_point = cable_path.coords[-1]
                        end_coords = {"lat": last_point[1], "lng": last_point[0]}
            
            result.append({
                "segment_id": segment.id,
                "segment_name": segment.name,
                "cable_id": segment.cable.id,
                "cable_name": segment.cable.name,
                "start_coords": start_coords,
                "end_coords": end_coords,
                "has_start_attachment": bool(segment.start_infrastructure),
                "has_end_attachment": bool(segment.end_infrastructure),
                "length_meters": segment.length_meters,
                "created_at": segment.created_at.isoformat() if segment.created_at else None
            })
        
        return Response({
            "status": "success",
            "count": len(result),
            "loose_ends": result
        }, status=status.HTTP_200_OK)
