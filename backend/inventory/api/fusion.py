"""
API endpoints for managing optical fiber fusions and splice box matrices.

This module implements the "digital twin" of physical splice boxes (CEOs),
allowing users to track which fibers are fused together and where (tray/slot).

CRITICAL LOGIC FIX (Phase 11.5):
- Fusion is ATOMIC 1:1 (Strand A <-> Strand B only)
- Physical slot occupation is independent of fiber color/number
- No "side effects" on other fibers in the same cable
- Validation: slot physical occupation + strand logical availability
"""
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.db import transaction
from django.shortcuts import get_object_or_404

from inventory.models import (
    FiberStrand,
    FiberInfrastructure,
    FiberCable,
)


class FusionViewSet(viewsets.ViewSet):
    """
    API for managing optical fiber fusions and splice box matrices.
    
    ATOMIC FUSION LOGIC:
    - Each slot holds exactly ONE fusion (pair of strands)
    - Fiber color/number does NOT determine slot position
    - Example: Cable A FO-12 (Aqua) can fuse with Cable B FO-4 (Blue) at Slot 1
    - This does NOT block Cable A FO-1 (Green) from using Slot 2
    
    Endpoints:
    - GET matrix/{infra_id}/ - View current fusion matrix state
    - POST fuse/ - Create fusion at specific tray/slot
    - POST disconnect/ - Remove fusion from tray/slot
    - GET box-context/{infra_id}/ - Get available cables/strands
    """
    permission_classes = [IsAuthenticated]

    @action(
        detail=False,
        methods=['get'],
        url_path='matrix/(?P<infra_id>[^/.]+)'
    )
    def get_matrix(self, request, infra_id=None):
        """
        Returns current fusion matrix state.
        
        IMPORTANT: Does NOT assume "Slot 1 = Fiber 1".
        Reads exactly what's stored in database.
        """
        box = get_object_or_404(
            FiberInfrastructure,
            id=infra_id,
            infrastructure_type='ceo'
        )

        # Find all strands that point to this box physically
        fusions = FiberStrand.objects.filter(
            fusion_infrastructure=box,
            fusion_tray__isnull=False,
            fusion_slot__isnull=False
        ).select_related(
            'tube__cable',
            'fused_to__tube__cable'
        )

        matrix_data = {}
        processed_ids = set()

        for strand in fusions:
            # Avoid duplicate pairs (A->B and B->A are same visual fusion)
            if strand.id in processed_ids:
                continue

            key = f"{strand.fusion_tray}-{strand.fusion_slot}"
            pair = strand.fused_to

            # Mark pair as processed
            if pair:
                processed_ids.add(pair.id)

            # Build visual structure for grid
            matrix_data[key] = {
                "tray": strand.fusion_tray,
                "slot": strand.fusion_slot,
                "fiber_a": {
                    "id": strand.id,
                    "name": f"FO {strand.number}",
                    "color_name": strand.color,
                    "cable": strand.tube.cable.label,
                    "cable_id": strand.tube.cable.id,
                    "color_hex": strand.color_hex,
                },
                "fiber_b": {
                    "id": pair.id if pair else None,
                    "name": f"FO {pair.number}" if pair else "Desconectado",
                    "color_name": pair.color if pair else "",
                    "cable": pair.tube.cable.label if pair else "N/A",
                    "cable_id": pair.tube.cable.id if pair else None,
                    "color_hex": pair.color_hex if pair else "#cccccc",
                } if pair else None
            }

        # Get template info for rendering tabs
        template_data = {
            "max_trays": 1,
            "splices_per_tray": 24
        }

        return Response({
            "box_name": box.name,
            "template": template_data,
            "matrix": matrix_data,
            "total_fusions": len(matrix_data),
        })

    @action(detail=False, methods=['post'])
    def fuse(self, request):
        """
        Creates atomic 1:1 fusion with auto-cleanup for free movement.
        
        Request:
        {
            "infrastructure_id": 123,
            "tray": 1,
            "slot": 5,
            "fiber_a": 456,  # Any fiber from Cable A
            "fiber_b": 789   # Any fiber from Cable B
        }
        
        Features:
        - Auto-disconnect previous fusions (allows moving fibers)
        - Slot overwrite behavior (replaces existing fusion)
        - Atomic operation with database locking
        
        Example:
            Move FO-1 from Slot 1 to Slot 2: ✓ Automatic cleanup
            Overwrite Slot 5 with new fusion: ✓ Old fusion removed
        """
        infra_id = request.data.get('infrastructure_id')
        tray = request.data.get('tray')
        slot = request.data.get('slot')
        id_a = request.data.get('fiber_a')
        id_b = request.data.get('fiber_b')

        # 1. Validate required parameters
        if not all([infra_id, tray, slot, id_a, id_b]):
            return Response(
                {
                    "error": (
                        "Parâmetros obrigatórios: infrastructure_id, "
                        "tray, slot, fiber_a, fiber_b"
                    )
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        # 2. Prevent fusion loop (A with A)
        if id_a == id_b:
            return Response(
                {
                    "error": (
                        "Loop detectado: Não é possível fundir uma fibra "
                        "com ela mesma"
                    )
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        with transaction.atomic():
            # Lock rows to prevent race conditions
            s_a = FiberStrand.objects.select_for_update().get(id=id_a)
            s_b = FiberStrand.objects.select_for_update().get(id=id_b)

            # CLEANUP 1: Disconnect previous fusions for fiber A
            if s_a.fused_to:
                old_pair = s_a.fused_to
                old_pair.fused_to = None
                old_pair.status = 'dark'
                old_pair.fusion_infrastructure = None
                old_pair.fusion_tray = None
                old_pair.fusion_slot = None
                old_pair.save()

            # CLEANUP 2: Disconnect previous fusions for fiber B
            if s_b.fused_to:
                old_pair = s_b.fused_to
                old_pair.fused_to = None
                old_pair.status = 'dark'
                old_pair.fusion_infrastructure = None
                old_pair.fusion_tray = None
                old_pair.fusion_slot = None
                old_pair.save()

            # CLEANUP 3: Clear target slot (overwrite behavior)
            occupants = FiberStrand.objects.filter(
                fusion_infrastructure_id=infra_id,
                fusion_tray=tray,
                fusion_slot=slot
            ).exclude(id__in=[id_a, id_b])

            for occ in occupants:
                if occ.fused_to:
                    occ.fused_to.fused_to = None
                    occ.fused_to.fusion_infrastructure = None
                    occ.fused_to.fusion_tray = None
                    occ.fused_to.fusion_slot = None
                    occ.fused_to.save()
                occ.fused_to = None
                occ.fusion_infrastructure = None
                occ.fusion_tray = None
                occ.fusion_slot = None
                occ.status = 'dark'
                occ.save()

            # 5. Execute fusion (bidirectional logical link)
            s_a.fused_to = s_b
            s_b.fused_to = s_a

            # 6. Record physical location (both legs point to same slot)
            s_a.fusion_infrastructure_id = infra_id
            s_a.fusion_tray = tray
            s_a.fusion_slot = slot

            s_b.fusion_infrastructure_id = infra_id
            s_b.fusion_tray = tray
            s_b.fusion_slot = slot

            # 7. Update visual status
            s_a.status = 'connected'
            s_b.status = 'connected'

            s_a.save()
            s_b.save()

        return Response({
            "status": "success",
            "message": "Fusão realizada com sucesso",
            "fusion": {
                "tray": tray,
                "slot": slot,
                "fiber_a": f"{s_a.tube.cable.label} FO-{s_a.number}",
                "fiber_b": f"{s_b.tube.cable.label} FO-{s_b.number}",
            }
        }, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=['post'])
    def disconnect(self, request):
        """
        Removes fusion by clearing both strands symmetrically.
        
        Request:
        {
            "infrastructure_id": 123,
            "tray": 1,
            "slot": 5
        }
        
        Finds strands at this physical location and unfuses them.
        """
        infra_id = request.data.get('infrastructure_id')
        tray = request.data.get('tray')
        slot = request.data.get('slot')

        if not all([infra_id, tray, slot]):
            return Response(
                {
                    "error": (
                        "Parâmetros obrigatórios: infrastructure_id, "
                        "tray, slot"
                    )
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        with transaction.atomic():
            # Find all strands at this physical slot
            strands = FiberStrand.objects.filter(
                fusion_infrastructure_id=infra_id,
                fusion_tray=tray,
                fusion_slot=slot
            )

            count = strands.count()
            if count == 0:
                return Response(
                    {"error": f"Slot {slot} da Bandeja {tray} está vazio"},
                    status=status.HTTP_404_NOT_FOUND
                )

            # Clear fusion for all strands at this slot
            for strand in strands:
                # Clear the bidirectional link (fused_to)
                if strand.fused_to:
                    pair = strand.fused_to
                    pair.fused_to = None
                    pair.fusion_infrastructure = None
                    pair.fusion_tray = None
                    pair.fusion_slot = None
                    pair.status = 'dark'
                    pair.save()
                
                # Clear this strand
                strand.fused_to = None
                strand.fusion_infrastructure = None
                strand.fusion_tray = None
                strand.fusion_slot = None
                strand.status = 'dark'
                strand.save()

        return Response({
            "status": "success",
            "message": f"Fusão desfeita ({count} fibras liberadas)"
        })

    @action(
        detail=False,
        methods=['get'],
        url_path='box-context/(?P<infra_id>[^/.]+)'
    )
    def box_context(self, request, infra_id=None):
        """
        Returns VIRTUAL SEGMENTS of cables at this splice box.
        
        If cable passes through (midspan/sangria), returns TWO segments:
        - INCOMING: Cable coming from origin
        - OUTGOING: Cable going to destination
        
        This prevents "short-circuit" where same fiber appears twice.
        """
        box = get_object_or_404(FiberInfrastructure, id=infra_id)

        # Find cables attached to this infrastructure point
        from inventory.models import InfrastructureCableAttachment
        
        attachments = InfrastructureCableAttachment.objects.filter(
            infrastructure=box
        ).select_related('cable__profile')

        # Build virtual segments
        segments = []
        
        for attachment in attachments:
            cable = attachment.cable
            is_pass_through = attachment.is_pass_through
            
            # SEGMENT 1: INCOMING (always present)
            # Cable arriving at this CEO
            segments.append(self._build_segment(
                cable=cable,
                direction='INCOMING',
                infra_id=infra_id,
                attachment=attachment
            ))
            
            # SEGMENT 2: OUTGOING (only for pass-through cables)
            # Cable leaving this CEO (sangria/midspan)
            if is_pass_through:
                segments.append(self._build_segment(
                    cable=cable,
                    direction='OUTGOING',
                    infra_id=infra_id,
                    attachment=attachment
                ))
        
        return Response(segments)
    
    def _build_segment(self, cable, direction, infra_id, attachment):
        """
        Builds a virtual cable segment for frontend display.
        
        Args:
            cable: FiberCable instance
            direction: 'INCOMING' or 'OUTGOING'
            infra_id: Infrastructure ID
            attachment: InfrastructureCableAttachment instance
        """
        # Build label based on direction
        if direction == 'INCOMING':
            label = f"{cable.name} (Entrada)"
        else:
            label = f"{cable.name} (Saída)"
        
        # Serialize tubes and strands
        tubes_data = []
        for tube in cable.tubes.all():
            strands_data = []
            for strand in tube.strands.all():
                # Check if fused in THIS CEO
                is_fused_here = (
                    strand.fused_to is not None and
                    strand.fusion_infrastructure_id == int(infra_id)
                )
                
                # Check if fused in OTHER CEO
                fused_elsewhere = (
                    strand.fused_to is not None and
                    strand.fusion_infrastructure_id != int(infra_id)
                )
                
                fusion_ceo_name = None
                if fused_elsewhere and strand.fusion_infrastructure:
                    fusion_ceo_name = strand.fusion_infrastructure.name
                
                # INCLUDE ALL FIBERS (fused or not)
                # Mark is_fused=True if fused HERE (blocks selection)
                strands_data.append({
                    "id": strand.id,
                    "number": strand.number,
                    "absolute_number": strand.absolute_number,
                    "color": strand.color,
                    "color_hex": strand.color_hex,
                    "status": strand.status,
                    "is_fused": is_fused_here,
                    "fused_elsewhere": fused_elsewhere,
                    "fusion_ceo": fusion_ceo_name,
                })
            
            if strands_data:  # Only include tubes with available strands
                tubes_data.append({
                    "id": tube.id,
                    "number": tube.number,
                    "color": tube.color,
                    "color_hex": tube.color_hex,
                    "strands": strands_data,
                })
        
        # Return virtual segment with unique ID
        return {
            "id": cable.id,  # Real cable ID
            "unique_id": f"{cable.id}_{direction}",  # Virtual segment ID
            "name": cable.name,
            "label": label,
            "direction": direction,
            "port_type": attachment.port_type,
            "profile_name": cable.profile.name if cable.profile else "N/A",
            "tubes": tubes_data,
        }

