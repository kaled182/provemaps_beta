"""API endpoint for cable-infrastructure attachments."""

from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from django.shortcuts import get_object_or_404

from inventory.models import (
    FiberCable,
    FiberInfrastructure,
    InfrastructureCableAttachment,
)


class CableAttachmentViewSet(viewsets.ViewSet):
    """
    ViewSet for managing cable attachments to infrastructure.
    """

    @action(detail=False, methods=['post'])
    def attach(self, request):
        """
        Attach a cable to an infrastructure point.
        
        Request:
        {
            "cable_id": 123,
            "infrastructure_id": 456,
            "port_type": "oval",  # ou "round"
            "is_pass_through": false
        }
        """
        cable_id = request.data.get('cable_id')
        infra_id = request.data.get('infrastructure_id')
        port_type = request.data.get('port_type', 'oval')
        is_pass_through = request.data.get('is_pass_through', False)

        if not cable_id or not infra_id:
            return Response(
                {"error": "cable_id e infrastructure_id são obrigatórios"},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Validar objetos
        cable = get_object_or_404(FiberCable, id=cable_id)
        infrastructure = get_object_or_404(
            FiberInfrastructure,
            id=infra_id
        )

        # Criar ou atualizar attachment
        attachment, created = (
            InfrastructureCableAttachment.objects.update_or_create(
                infrastructure=infrastructure,
                cable=cable,
                port_type=port_type,
                defaults={
                    'is_pass_through': is_pass_through
                }
            )
        )

        return Response({
            "status": "success",
            "message": (
                f"Cabo {cable.name} anexado a "
                f"{infrastructure.name}"
            ),
            "attachment_id": attachment.id,
            "created": created,
            "port_type": attachment.port_type,
            "is_pass_through": attachment.is_pass_through,
        }, status=status.HTTP_201_CREATED if created else status.HTTP_200_OK)

    @action(detail=False, methods=['post'])
    def detach(self, request):
        """
        Detach a cable from an infrastructure point.
        
        Request:
        {
            "cable_id": 123,
            "infrastructure_id": 456
        }
        """
        cable_id = request.data.get('cable_id')
        infra_id = request.data.get('infrastructure_id')

        if not cable_id or not infra_id:
            return Response(
                {"error": "cable_id e infrastructure_id são obrigatórios"},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Deletar attachment se existir
        deleted_count, _ = InfrastructureCableAttachment.objects.filter(
            infrastructure_id=infra_id,
            cable_id=cable_id
        ).delete()

        if deleted_count == 0:
            return Response(
                {"error": "Anexação não encontrada"},
                status=status.HTTP_404_NOT_FOUND
            )

        return Response({
            "status": "success",
            "message": "Cabo desanexado da infraestrutura",
            "deleted_count": deleted_count
        })
