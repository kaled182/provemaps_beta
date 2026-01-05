"""
API endpoint para anexar pontas soltas de cabos rompidos a CEOs.

Endpoint: POST /api/v1/inventory/infrastructure/<ceo_id>/attach-loose-end/

Payload:
{
    "cable_id": 123,
    "segment_id": 456,
    "is_start_of_segment": true
}
"""
import logging

from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from inventory.models import (
    FiberCable,
    FiberInfrastructure,
    CableSegment,
    InfrastructureCableAttachment,
)

logger = logging.getLogger(__name__)


class AttachLooseEndView(APIView):
    """
    Anexa uma ponta solta (loose end) de um cabo rompido a uma CEO.
    
    Usado após romper um cabo para conectar manualmente as pontas.
    """

    def post(self, request, infrastructure_id):
        cable_id = request.data.get('cable_id')
        segment_id = request.data.get('segment_id')
        is_start = request.data.get('is_start_of_segment', True)
        
        if not cable_id or not segment_id:
            return Response(
                {"error": "cable_id e segment_id são obrigatórios"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        infrastructure = get_object_or_404(
            FiberInfrastructure,
            id=infrastructure_id,
            type='splice_box'
        )
        cable = get_object_or_404(FiberCable, id=cable_id)
        segment = get_object_or_404(
            CableSegment,
            id=segment_id,
            cable=cable
        )
        
        logger.info(f"[ATTACH_LOOSE_END] Anexando ponta solta:")
        logger.info(f"  - CEO: {infrastructure.name} (ID {infrastructure.id})")
        logger.info(f"  - Cabo: {cable.name} (ID {cable.id})")
        logger.info(f"  - Segmento: {segment.name} (ID {segment.id})")
        logger.info(f"  - Ponta: {'INÍCIO' if is_start else 'FIM'} do segmento")
        
        # Verificar se já existe attachment para este segmento
        existing = InfrastructureCableAttachment.objects.filter(
            infrastructure=infrastructure,
            cable=cable,
            connected_segment=segment,
            is_start_of_segment=is_start
        ).first()
        
        if existing:
            logger.warning(f"[ATTACH_LOOSE_END] Attachment já existe: {existing.id}")
            return Response(
                {
                    "status": "already_attached",
                    "message": "Esta ponta já está anexada a esta CEO",
                    "attachment_id": existing.id
                },
                status=status.HTTP_200_OK
            )
        
        # Criar novo attachment
        attachment = InfrastructureCableAttachment.objects.create(
            infrastructure=infrastructure,
            cable=cable,
            connected_segment=segment,
            is_start_of_segment=is_start,
            port_type='oval',  # Default: oval (passagem)
            is_pass_through=False
        )
        
        logger.info(f"[ATTACH_LOOSE_END] Attachment criado: ID {attachment.id}")
        
        # Verificar se ambas as pontas do segmento estão conectadas
        start_attached = InfrastructureCableAttachment.objects.filter(
            cable=cable,
            connected_segment=segment,
            is_start_of_segment=True
        ).exists()
        
        end_attached = InfrastructureCableAttachment.objects.filter(
            cable=cable,
            connected_segment=segment,
            is_start_of_segment=False
        ).exists()
        
        both_connected = start_attached and end_attached
        
        # Se ambas as pontas estão conectadas, marcar has_loose_ends=False
        if both_connected and segment.has_loose_ends:
            segment.has_loose_ends = False
            segment.save(update_fields=['has_loose_ends'])
            logger.info(f"[ATTACH_LOOSE_END] Segmento {segment.name} totalmente conectado - has_loose_ends=False")
        
        return Response({
            "status": "success",
            "message": f"Ponta anexada à CEO {infrastructure.name}",
            "attachment": {
                "id": attachment.id,
                "infrastructure_id": infrastructure.id,
                "infrastructure_name": infrastructure.name,
                "cable_id": cable.id,
                "cable_name": cable.name,
                "segment_id": segment.id,
                "segment_name": segment.name,
                "is_start_of_segment": is_start,
            },
            "both_ends_connected": both_connected,
            "ready_for_fusion": both_connected
        }, status=status.HTTP_201_CREATED)
