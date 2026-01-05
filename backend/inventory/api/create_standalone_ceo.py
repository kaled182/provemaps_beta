"""
API endpoint para criar CEO independente (não anexada a cabo).

Endpoint: POST /api/v1/inventory/infrastructure/create-standalone-ceo/

Payload:
{
    "name": "CEO-Centro-01",
    "lat": -15.123,
    "lng": -47.456
}
"""
import logging

from django.contrib.gis.geos import Point
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from inventory.models import FiberInfrastructure

logger = logging.getLogger(__name__)


class CreateStandaloneCEOView(APIView):
    """
    Cria uma CEO independente em qualquer lugar do mapa (não anexada a cabo).
    
    Usado para criar CEOs antes de romper o cabo e depois arrastar as pontas.
    """

    def post(self, request):
        name = request.data.get('name')
        lat = request.data.get('lat')
        lng = request.data.get('lng')
        
        if not name or not lat or not lng:
            return Response(
                {"error": "name, lat e lng são obrigatórios"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            lat = float(lat)
            lng = float(lng)
        except (ValueError, TypeError):
            return Response(
                {"error": "lat e lng devem ser números válidos"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        logger.info(f"[CREATE_STANDALONE_CEO] Criando CEO independente:")
        logger.info(f"  - Nome: {name}")
        logger.info(f"  - Localização: ({lat}, {lng})")
        
        # Criar CEO sem associação a cabo
        location = Point(lng, lat, srid=4326)
        
        ceo = FiberInfrastructure.objects.create(
            cable=None,  # Não associado a nenhum cabo
            type='splice_box',
            name=name,
            location=location,
            distance_from_origin=None,  # Não tem distância pois não está em cabo
            metadata={"standalone": True, "created_for_loose_ends": True}
        )
        
        logger.info(f"[CREATE_STANDALONE_CEO] CEO criada: ID {ceo.id}")
        
        return Response({
            "status": "success",
            "message": f"CEO {name} criada com sucesso",
            "ceo": {
                "id": ceo.id,
                "name": ceo.name,
                "type": ceo.type,
                "type_display": ceo.get_type_display(),
                "location": {
                    "lat": ceo.location.y,
                    "lng": ceo.location.x
                },
                "standalone": True
            }
        }, status=status.HTTP_201_CREATED)
