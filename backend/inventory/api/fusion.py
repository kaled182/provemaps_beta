"""
API endpoints for managing optical fiber fusions and splice box matrices.

This module implements the "digital twin" of physical splice boxes (CEOs),
allowing users to track which fibers are fused together and where (tray/slot).
"""
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.db import transaction
from django.shortcuts import get_object_or_404
from django.db.models import Q

from inventory.models import (
    FiberStrand,
    FiberInfrastructure,
    FiberCable,
    BufferTube,
)


class FusionViewSet(viewsets.ViewSet):
    """
    API for managing optical fiber fusions and splice box matrices.
    
    Endpoints:
    - GET matrix/{infra_id}/ - View current fusion matrix state
    - POST fuse/ - Create a new fusion at specific tray/slot
    - DELETE unfuse/{strand_id}/ - Remove fusion
    - GET box-context/{infra_id}/ - Get cables near the splice box
    """
    permission_classes = [IsAuthenticated]

    @action(detail=False, methods=['get'], url_path='matrix/(?P<infra_id>[^/.]+)')
    def get_matrix(self, request, infra_id=None):
        """
        Returns the current state of the fusion matrix (which slots are occupied).
        
        Response format:
        {
            "box_name": "CEO-01-BKB",
            "template": {"max_trays": 4, "splices_per_tray": 24},
            "installed_trays": 2,
            "matrix": {
                "1-1": {
                    "tray": 1,
                    "slot": 1,
                    "fiber_a": {"id": 123, "name": "FO 12 (verde)", "cable": "CB-001"},
                    "fiber_b": {"id": 456, "name": "FO 1 (azul)", "cable": "CB-002"}
                },
                ...
            }
        }
        """
        box = get_object_or_404(FiberInfrastructure, id=infra_id, type='splice_box')

        # Find all fusions that happened in this box
        fusions = FiberStrand.objects.filter(
            fusion_infrastructure=box
        ).select_related(
            'tube__cable',
            'fused_to__tube__cable'
        ).prefetch_related(
            'tube__cable__profile'
        )

        matrix_data = {}
        
        for fiber in fusions:
            if fiber.fusion_tray and fiber.fusion_slot:
                key = f"{fiber.fusion_tray}-{fiber.fusion_slot}"
                
                # Avoid duplicates (fusion is bidirectional)
                if key in matrix_data:
                    continue
                
                pair = fiber.fused_to
                
                matrix_data[key] = {
                    "tray": fiber.fusion_tray,
                    "slot": fiber.fusion_slot,
                    "fiber_a": {
                        "id": fiber.id,
                        "name": f"FO {fiber.number} ({fiber.color})",
                        "cable": fiber.tube.cable.name,
                        "cable_id": fiber.tube.cable.id,
                        "color_hex": fiber.color_hex,
                    },
                    "fiber_b": {
                        "id": pair.id if pair else None,
                        "name": f"FO {pair.number} ({pair.color})" if pair else "?",
                        "cable": pair.tube.cable.name if pair else "?",
                        "cable_id": pair.tube.cable.id if pair else None,
                        "color_hex": pair.color_hex if pair else "#cccccc",
                    } if pair else None
                }

        # Get template info
        template_data = {
            "max_trays": 1,
            "splices_per_tray": 24
        }
        
        if box.box_template:
            template_data = {
                "max_trays": box.box_template.max_trays,
                "splices_per_tray": box.box_template.splices_per_tray,
            }

        return Response({
            "box_name": box.name or f"CEO @ {box.distance_from_origin:.0f}m",
            "template": template_data,
            "installed_trays": box.installed_trays,
            "matrix": matrix_data,
            "total_fusions": len(matrix_data),
        })

    @action(detail=False, methods=['post'])
    def fuse(self, request):
        """
        Creates a new fusion at a specific tray/slot position.
        
        Request body:
        {
            "infrastructure_id": 123,
            "tray": 1,
            "slot": 5,
            "fiber_a": 456,
            "fiber_b": 789
        }
        
        Validations:
        - Slot must be free
        - Fibers must not already be fused
        - Fibers must be from different cables
        """
        infra_id = request.data.get('infrastructure_id')
        tray = request.data.get('tray')
        slot = request.data.get('slot')
        fiber_a_id = request.data.get('fiber_a')
        fiber_b_id = request.data.get('fiber_b')

        # Validate required fields
        if not all([infra_id, tray, slot, fiber_a_id, fiber_b_id]):
            return Response(
                {"error": "Campos obrigatórios: infrastructure_id, tray, slot, fiber_a, fiber_b"},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            tray = int(tray)
            slot = int(slot)
        except (TypeError, ValueError):
            return Response(
                {"error": "Tray e slot devem ser números inteiros"},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Validate slot range
        if slot < 1 or slot > 24:
            return Response(
                {"error": "Slot deve estar entre 1 e 24"},
                status=status.HTTP_400_BAD_REQUEST
            )

        with transaction.atomic():
            # Check if slot is occupied
            occupied = FiberStrand.objects.filter(
                fusion_infrastructure_id=infra_id,
                fusion_tray=tray,
                fusion_slot=slot
            ).exists()

            if occupied:
                return Response(
                    {"error": f"Slot {slot} da Bandeja {tray} já está ocupado"},
                    status=status.HTTP_409_CONFLICT
                )

            # Get fibers
            try:
                strand_a = FiberStrand.objects.select_related('tube__cable').get(id=fiber_a_id)
                strand_b = FiberStrand.objects.select_related('tube__cable').get(id=fiber_b_id)
            except FiberStrand.DoesNotExist:
                return Response(
                    {"error": "Uma ou ambas as fibras não foram encontradas"},
                    status=status.HTTP_404_NOT_FOUND
                )

            # Validate fibers are not already fused
            if strand_a.fused_to or strand_b.fused_to:
                return Response(
                    {"error": "Uma das fibras já está fusionada. Desfaça a fusão anterior primeiro."},
                    status=status.HTTP_409_CONFLICT
                )

            # Validate fibers are from different cables
            if strand_a.tube.cable.id == strand_b.tube.cable.id:
                return Response(
                    {"error": "Não é possível fusionar fibras do mesmo cabo"},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # Perform fusion (bidirectional)
            strand_a.fused_to = strand_b
            strand_b.fused_to = strand_a

            # Record physical location (both fibers point to same slot)
            strand_a.fusion_infrastructure_id = infra_id
            strand_a.fusion_tray = tray
            strand_a.fusion_slot = slot

            strand_b.fusion_infrastructure_id = infra_id
            strand_b.fusion_tray = tray
            strand_b.fusion_slot = slot

            strand_a.save(update_fields=['fused_to', 'fusion_infrastructure', 'fusion_tray', 'fusion_slot'])
            strand_b.save(update_fields=['fused_to', 'fusion_infrastructure', 'fusion_tray', 'fusion_slot'])

        return Response({
            "status": "success",
            "message": f"Fusão criada no slot {slot} da bandeja {tray}",
            "fusion": {
                "tray": tray,
                "slot": slot,
                "fiber_a": f"{strand_a.tube.cable.name} FO{strand_a.number}",
                "fiber_b": f"{strand_b.tube.cable.name} FO{strand_b.number}",
            }
        }, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=['delete'], url_path='unfuse/(?P<strand_id>[^/.]+)')
    def unfuse(self, request, strand_id=None):
        """
        Removes a fusion by clearing the fused_to relationship and matrix position.
        """
        try:
            strand = FiberStrand.objects.select_related('fused_to').get(id=strand_id)
        except FiberStrand.DoesNotExist:
            return Response(
                {"error": "Fibra não encontrada"},
                status=status.HTTP_404_NOT_FOUND
            )

        if not strand.fused_to:
            return Response(
                {"error": "Esta fibra não está fusionada"},
                status=status.HTTP_400_BAD_REQUEST
            )

        with transaction.atomic():
            pair = strand.fused_to

            # Clear fusion (bidirectional)
            strand.fused_to = None
            strand.fusion_infrastructure = None
            strand.fusion_tray = None
            strand.fusion_slot = None

            pair.fused_to = None
            pair.fusion_infrastructure = None
            pair.fusion_tray = None
            pair.fusion_slot = None

            strand.save(update_fields=['fused_to', 'fusion_infrastructure', 'fusion_tray', 'fusion_slot'])
            pair.save(update_fields=['fused_to', 'fusion_infrastructure', 'fusion_tray', 'fusion_slot'])

        return Response({
            "status": "success",
            "message": "Fusão removida com sucesso"
        })

    @action(detail=False, methods=['get'], url_path='box-context/(?P<infra_id>[^/.]+)')
    def box_context(self, request, infra_id=None):
        """
        Returns cables that pass through or connect to this splice box.
        Used to populate the cable selection lists in the fusion modal.
        
        Returns full cable structure (tubes + strands) for visual selection.
        """
        box = get_object_or_404(FiberInfrastructure, id=infra_id)

        # Find cables attached to this infrastructure point
        from inventory.models import InfrastructureCableAttachment
        
        attachments = InfrastructureCableAttachment.objects.filter(
            infrastructure=box
        ).select_related('cable').values_list('cable_id', flat=True)

        # If no explicit attachments, find cables that own this infrastructure
        cable_ids = list(attachments)
        if not cable_ids and box.cable_id:
            cable_ids = [box.cable_id]

        # Get full cable structures
        cables = FiberCable.objects.filter(
            id__in=cable_ids
        ).prefetch_related(
            'tubes__strands'
        )

        # Serialize cables with tubes and strands
        result = []
        for cable in cables:
            tubes_data = []
            for tube in cable.tubes.all():
                strands_data = []
                for strand in tube.strands.all():
                    # Only include unfused or fibers fused at this box
                    include_strand = (
                        not strand.fused_to or 
                        strand.fusion_infrastructure_id == int(infra_id)
                    )
                    
                    if include_strand:
                        strands_data.append({
                            "id": strand.id,
                            "number": strand.number,
                            "absolute_number": strand.absolute_number,
                            "color": strand.color,
                            "color_hex": strand.color_hex,
                            "status": strand.status,
                            "is_fused": strand.fused_to is not None,
                        })
                
                if strands_data:  # Only include tubes with available strands
                    tubes_data.append({
                        "id": tube.id,
                        "number": tube.number,
                        "color": tube.color,
                        "color_hex": tube.color_hex,
                        "strands": strands_data,
                    })

            result.append({
                "id": cable.id,
                "name": cable.name,
                "tubes": tubes_data,
            })

        return Response(result)
