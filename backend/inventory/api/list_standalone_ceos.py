"""
API endpoint para listar CEOs standalone (não anexadas a cabos).

Endpoint: GET /api/v1/inventory/infrastructure/standalone-ceos/
"""
import logging

from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from inventory.models import FiberInfrastructure

logger = logging.getLogger(__name__)


class ListStandaloneCEOsView(APIView):
    """
    Lista todas as CEOs standalone (sem cabo associado).
    """

    def get(self, request):
        # Buscar CEOs sem cabo associado
        standalone_ceos = FiberInfrastructure.objects.filter(
            cable__isnull=True,
            type='splice_box'
        )
        
        logger.info(f"[LIST_STANDALONE_CEOS] Encontradas {standalone_ceos.count()} CEOs standalone")
        
        result = []
        for ceo in standalone_ceos:
            result.append({
                "id": ceo.id,
                "name": ceo.name,
                "type": ceo.type,
                "type_display": ceo.get_type_display(),
                "location": {
                    "lat": ceo.location.y,
                    "lng": ceo.location.x
                } if ceo.location else None,
                "metadata": ceo.metadata,
                "created_at": ceo.created_at.isoformat() if ceo.created_at else None
            })
        
        return Response({
            "status": "success",
            "count": len(result),
            "ceos": result
        }, status=status.HTTP_200_OK)
