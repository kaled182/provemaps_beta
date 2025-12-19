"""
API endpoints for managing optical fiber fusions and splice box matrices.

This module implements the "digital twin" of physical splice boxes (CEOs),
allowing users to track which fibers are fused together and where (tray/slot).

CRITICAL FUSION RULES:
1. Fusion is ATOMIC 1:1 (Strand A <-> Strand B only)
2. ⚠️ DIFFERENT CABLES ONLY: Cannot fuse fibers from the same cable (loop prevention)
3. Any fiber color can fuse with any other fiber color (cross-color fusion allowed)
4. Physical slot occupation is independent of fiber color/number
5. Validation: slot occupation + strand availability + cable loop prevention
"""
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.db import transaction
from django.db.models import Q
from django.shortcuts import get_object_or_404

from inventory.models import (
    FiberStrand,
    FiberInfrastructure,
    FiberCable,
    FiberFusion,
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
        Returns current fusion matrix state using FiberFusion model.
        
        IMPORTANT: Does NOT assume "Slot 1 = Fiber 1".
        Reads exactly what's stored in FiberFusion table.
        """
        box = get_object_or_404(
            FiberInfrastructure,
            id=infra_id,
            infrastructure_type='ceo'
        )

        # Find all fusions in this CEO using FiberFusion model
        fusions = FiberFusion.objects.filter(
            infrastructure=box
        ).select_related(
            'fiber_a__tube__cable',
            'fiber_b__tube__cable'
        ).order_by('tray', 'slot')

        matrix_data = {}

        for fusion in fusions:
            key = f"{fusion.tray}-{fusion.slot}"

            # Build visual structure for grid
            matrix_data[key] = {
                "tray": fusion.tray,
                "slot": fusion.slot,
                "fiber_a": {
                    "id": fusion.fiber_a.id,
                    "name": f"FO {fusion.fiber_a.number}",
                    "color_name": fusion.fiber_a.color,
                    "cable": fusion.fiber_a.tube.cable.name,
                    "cable_id": fusion.fiber_a.tube.cable.id,
                    "color_hex": fusion.fiber_a.color_hex,
                },
                "fiber_b": {
                    "id": fusion.fiber_b.id,
                    "name": f"FO {fusion.fiber_b.number}",
                    "color_name": fusion.fiber_b.color,
                    "cable": fusion.fiber_b.tube.cable.name,
                    "cable_id": fusion.fiber_b.tube.cable.id,
                    "color_hex": fusion.fiber_b.color_hex,
                }
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
        Creates atomic 1:1 fusion using FiberFusion model.
        
        Request:
        {
            "infrastructure_id": 123,
            "tray": 1,
            "slot": 5,
            "fiber_a": 456,  # Fiber from INCOMING segment (left side)
            "fiber_b": 789   # Fiber from OUTGOING segment (right side)
        }
        
        CRITICAL CONVENTION:
        - fiber_a MUST be from INCOMING segment (left side of CEO)
        - fiber_b MUST be from OUTGOING segment (right side of CEO)
        - This ensures each virtual segment shows only its own fusions
        
        Features:
        - Auto-disconnect previous fusions (allows moving fibers)
        - Slot overwrite behavior (replaces existing fusion)
        - Atomic operation with database locking
        - Each CEO is completely independent (no cross-CEO interference)
        
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
            # Lock strands to prevent race conditions
            s_a = FiberStrand.objects.select_for_update().get(id=id_a)
            s_b = FiberStrand.objects.select_for_update().get(id=id_b)
            
            # 3. Prevent cable loop (same cable on both sides)
            if s_a.tube.cable_id == s_b.tube.cable_id:
                return Response(
                    {
                        "error": (
                            "Loop de cabo detectado: Não é possível fundir "
                            "fibras do mesmo cabo. Escolha fibras de cabos diferentes."
                        )
                    },
                    status=status.HTTP_400_BAD_REQUEST
                )

            # CLEANUP 1: Remove any existing fusions for fiber A in THIS CEO
            # fiber_a comes from INCOMING segment, so only remove where it's fiber_a
            FiberFusion.objects.filter(
                infrastructure_id=infra_id,
                fiber_a=s_a
            ).delete()

            # CLEANUP 2: Remove any existing fusions for fiber B in THIS CEO
            # fiber_b comes from OUTGOING segment, so only remove where it's fiber_b
            FiberFusion.objects.filter(
                infrastructure_id=infra_id,
                fiber_b=s_b
            ).delete()

            # CLEANUP 3: Clear target slot (overwrite behavior)
            # Remove any fusion that occupies this slot
            FiberFusion.objects.filter(
                infrastructure_id=infra_id,
                tray=tray,
                slot=slot
            ).delete()

            # 4. Create new fusion in FiberFusion table
            fusion = FiberFusion.objects.create(
                infrastructure_id=infra_id,
                tray=tray,
                slot=slot,
                fiber_a=s_a,
                fiber_b=s_b
            )
            
            # DEBUG LOG
            print(f"[FUSION DEBUG] Created fusion in CEO {infra_id}, Slot {tray}-{slot}:")
            print(f"  fiber_a: ID={s_a.id}, Color={s_a.color}, Cable={s_a.tube.cable.name}")
            print(f"  fiber_b: ID={s_b.id}, Color={s_b.color}, Cable={s_b.tube.cable.name}")

            # 5. Update strand status to 'connected' (visual indicator)
            # Note: Strands can have multiple fusions across different CEOs
            # The status reflects the most recent or primary connection
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
                "fiber_a": f"{s_a.tube.cable.name} FO-{s_a.number}",
                "fiber_b": f"{s_b.tube.cable.name} FO-{s_b.number}",
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
            # Find fusion at this slot using FiberFusion model
            fusion = FiberFusion.objects.filter(
                infrastructure_id=infra_id,
                tray=tray,
                slot=slot
            ).first()

            if not fusion:
                return Response(
                    {"error": f"Slot {slot} da Bandeja {tray} está vazio"},
                    status=status.HTTP_404_NOT_FOUND
                )

            # Get the fibers before deleting
            fiber_a = fusion.fiber_a
            fiber_b = fusion.fiber_b

            # Delete the fusion
            fusion.delete()

            # Update strand status to 'dark' if no other fusions exist
            # (Check if fiber has fusions in other CEOs)
            a_has_other_fusions = FiberFusion.objects.filter(
                Q(fiber_a=fiber_a) | Q(fiber_b=fiber_a)
            ).exists()
            
            b_has_other_fusions = FiberFusion.objects.filter(
                Q(fiber_a=fiber_b) | Q(fiber_b=fiber_b)
            ).exists()

            if not a_has_other_fusions:
                fiber_a.status = 'dark'
                fiber_a.save()
            
            if not b_has_other_fusions:
                fiber_b.status = 'dark'
                fiber_b.save()

        return Response({
            "status": "success",
            "message": "Fusão desfeita com sucesso"
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
        from inventory.models import FiberFusion
        
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
                # CRITICAL LOGIC FOR VIRTUAL SEGMENTS:
                # When a cable passes through a CEO, it has TWO virtual segments:
                # - INCOMING (left side): Shows fusions where this strand is fiber_a
                # - OUTGOING (right side): Shows fusions where this strand is fiber_b
                # 
                # This prevents the same physical strand from being blocked on BOTH sides
                # when it's only fused on ONE side of the CEO.
                #
                # CONVENTION:
                # - fiber_a in FiberFusion = strand from INCOMING segment (left)
                # - fiber_b in FiberFusion = strand from OUTGOING segment (right)
                
                is_fused_here = False
                
                if direction == 'INCOMING':
                    # For INCOMING segment, only check if this strand is fiber_a
                    fusion_here = FiberFusion.objects.filter(
                        infrastructure_id=int(infra_id),
                        fiber_a=strand  # Only check fiber_a side
                    ).first()
                    is_fused_here = fusion_here is not None
                    
                    # DEBUG LOG
                    if fusion_here:
                        print(f"[FUSION DEBUG] INCOMING: Strand {strand.id} ({strand.color}) is fiber_a in fusion → BLOCKED")
                    
                else:  # OUTGOING
                    # For OUTGOING segment, only check if this strand is fiber_b
                    fusion_here = FiberFusion.objects.filter(
                        infrastructure_id=int(infra_id),
                        fiber_b=strand  # Only check fiber_b side
                    ).first()
                    is_fused_here = fusion_here is not None
                    
                    # DEBUG LOG
                    if fusion_here:
                        print(f"[FUSION DEBUG] OUTGOING: Strand {strand.id} ({strand.color}) is fiber_b in fusion → BLOCKED")
                
                # EACH CEO IS INDEPENDENT - Never show fusions from other CEOs
                # No fused_elsewhere, no fusion_ceo - completely isolated
                strands_data.append({
                    "id": strand.id,
                    "number": strand.number,
                    "absolute_number": strand.absolute_number,
                    "color": strand.color,
                    "color_hex": strand.color_hex,
                    "status": strand.status,
                    "is_fused": is_fused_here,  # Only TRUE if fused on THIS side of THIS CEO
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

