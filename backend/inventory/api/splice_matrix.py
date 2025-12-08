from __future__ import annotations

from typing import Any

from django.http import Http404
from rest_framework.request import Request
from django.db import transaction
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from inventory.models import (
    FiberInfrastructure,
    FiberStrand,
    FiberCable,
)


"""Splice matrix and context API views.

pyright: reportUnknownMemberType=false, reportUnknownVariableType=false,
    reportUnknownParameterType=false, reportUnknownAttributeUsage=false
"""


class SpliceBoxMatrixView(APIView):
    """
    GET /api/v1/splice-boxes/<id>/matrix

    Retorna a matriz de ocupação (bandeja/slot) de uma CEO, baseada
    em `FiberStrand.fusion_infrastructure`, `fusion_tray`, `fusion_slot`.
    
    Agora com informações completas da fusão (fiber_a ↔ fiber_b).
    """

    def get(self, request: Request, id: int) -> Response:
        try:
            infra = FiberInfrastructure.objects.get(pk=id)
        except FiberInfrastructure.DoesNotExist:
            raise Http404("Splice box (infrastructure) não encontrada")

        # Buscar todas as fusões nesta CEO
        fusions = (
            FiberStrand.objects.filter(fusion_infrastructure=infra)
            .select_related(
                'tube__cable',
                'tube__cable__site_a',
                'tube__cable__site_b',
                'fused_to__tube__cable',
                'fused_to__tube__cable__site_a',
                'fused_to__tube__cable__site_b',
            )
            .prefetch_related('tube__cable__profile')
        )

        matrix_data = {}
        
        for fiber in fusions:
            if fiber.fusion_tray and fiber.fusion_slot:
                key = f"{fiber.fusion_tray}-{fiber.fusion_slot}"
                # Evitar duplicatas (registrar apenas uma vez por slot)
                if key in matrix_data:
                    continue
                pair = fiber.fused_to
                is_repair = pair is None
                fiber_a_payload = self._serialize_fiber(fiber, infra)
                fiber_b_payload = None

                if pair:
                    fiber_b_payload = self._serialize_fiber(pair, infra)
                elif is_repair:
                    fiber_b_payload = self._serialize_fiber(fiber, infra)

                matrix_data[key] = {
                    "tray": fiber.fusion_tray,
                    "slot": fiber.fusion_slot,
                    "is_repair": is_repair,
                    "fiber_a": fiber_a_payload,
                    "fiber_b": fiber_b_payload,
                }

        # Template info
        template_data = {
            "max_trays": infra.installed_trays or 1,
            "splices_per_tray": 24
        }
        
        if infra.box_template:
            template_data = {
                "max_trays": infra.box_template.max_trays,
                "splices_per_tray": infra.box_template.splices_per_tray,
            }

        box_name = (
            infra.name
            if infra.name
            else f"CEO @ {infra.distance_from_origin:.0f}m"
        )
        payload = {
            "infrastructure_id": infra.id,
            "box_name": box_name,
            "template": template_data,
            "installed_trays": infra.installed_trays or 1,
            "matrix": matrix_data,
            "total_fusions": len(matrix_data),
        }
        return Response(payload, status=status.HTTP_200_OK)

    @staticmethod
    def _serialize_fiber(
        strand: FiberStrand,
        infra: FiberInfrastructure,
    ) -> dict[str, Any]:
        cable = strand.tube.cable
        direction = SpliceBoxMatrixView._resolve_direction_payload(
            cable,
            infra,
        )

        return {
            "id": strand.id,
            "number": strand.number,
            "absolute_number": strand.absolute_number,
            "color": strand.color,
            "color_hex": strand.color_hex,
            "color_name": strand.color,
            "cable": cable.name,
            "cable_id": cable.id,
            "direction": direction["remote"],
            "direction_label": direction["label"],
            "direction_a": direction["a"],
            "direction_b": direction["b"],
            "fiber_code": f"T{strand.tube.number}F{strand.number}",
            "tube_number": strand.tube.number,
            "tube_color": strand.tube.color,
            "tube_color_hex": strand.tube.color_hex,
        }

    @staticmethod
    def _resolve_direction_payload(
        cable: FiberCable,
        infra: FiberInfrastructure,
    ) -> dict[str, str | None]:
        box_label = infra.name or f"CEO-{infra.id}"
        site_a = (
            cable.site_a.display_name
            if getattr(cable, "site_a", None)
            else None
        )
        site_b = (
            cable.site_b.display_name
            if getattr(cable, "site_b", None)
            else None
        )

        direction_label = cable.name
        if site_a and site_b:
            direction_label = f"{site_a} → {site_b}"
        elif site_a:
            direction_label = f"{site_a} → {box_label}"
        elif site_b:
            direction_label = f"{box_label} → {site_b}"

        remote = site_a or site_b or box_label

        return {
            "label": direction_label,
            "remote": remote,
            "a": site_a or box_label,
            "b": site_b or box_label,
        }


class CreateFusionView(APIView):
    """
    POST /api/v1/fusions/

    Body esperado (ATUALIZADO para fusão bidirecional):
    - infrastructure_id: int (CEO onde ocorre a fusão)
    - tray: int
    - slot: int (1–24)
    - fiber_a: int (primeira fibra)
    - fiber_b: int (segunda fibra) - NOVO!

    Regras:
    - Se já existir fibra ocupando mesmo (infra, tray, slot) → 409 Conflict
    - Fibras devem ser de cabos diferentes
    - Marca `fused_to` bidirecional e posição física (tray/slot)
    """

    def post(self, request: Request) -> Response:
        data = request.data or {}
        infra_id = data.get("infrastructure_id")
        tray = data.get("tray")
        slot = data.get("slot")
        fiber_a_id = data.get("fiber_a")
        fiber_b_id = data.get("fiber_b")

        if not all([infra_id, tray, slot, fiber_a_id, fiber_b_id]):
            return Response(
                {
                    "detail": (
                        "Campos obrigatórios: infrastructure_id, tray, "
                        "slot, fiber_a, fiber_b"
                    )
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            tray = int(tray)
            slot = int(slot)
        except (TypeError, ValueError):
            return Response(
                {"detail": "Tray e slot devem ser números inteiros"},
                status=status.HTTP_400_BAD_REQUEST
            )

        if slot < 1 or slot > 24:
            return Response(
                {"detail": "Slot inválido (1–24)"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            infra = FiberInfrastructure.objects.get(pk=infra_id)
        except FiberInfrastructure.DoesNotExist:
            return Response(
                {"detail": "Infraestrutura não encontrada"},
                status=status.HTTP_404_NOT_FOUND,
            )

        trays = infra.installed_trays or 1
        if tray < 1 or tray > trays:
            return Response(
                {"detail": f"Bandeja inválida (1–{trays})"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        with transaction.atomic():
            # Verificar se slot está livre
            existing = FiberStrand.objects.filter(
                fusion_infrastructure_id=infra.id,
                fusion_tray=tray,
                fusion_slot=slot,
            ).first()
            
            if existing:
                return Response(
                    {
                        "detail": (
                            f"Slot {slot} da Bandeja {tray} já está ocupado"
                        ),
                        "occupied_by_fiber_id": existing.id,
                    },
                    status=status.HTTP_409_CONFLICT,
                )

            # Buscar fibras
            try:
                strand_a = FiberStrand.objects.select_related(
                    'tube__cable'
                ).get(pk=fiber_a_id)
                strand_b = FiberStrand.objects.select_related(
                    'tube__cable'
                ).get(pk=fiber_b_id)
            except FiberStrand.DoesNotExist:
                return Response(
                    {"detail": "Uma ou ambas as fibras não foram encontradas"},
                    status=status.HTTP_404_NOT_FOUND,
                )
            
            # Caso reparo: mesma fibra nos dois lados (sem fused_to)
            if fiber_a_id == fiber_b_id:
                strand_a.fusion_infrastructure = infra
                strand_a.fusion_tray = tray
                strand_a.fusion_slot = slot
                strand_a.fused_to = None  # Não fusiona consigo mesma
                strand_a.save(
                    update_fields=[
                        'fusion_infrastructure',
                        'fusion_tray',
                        'fusion_slot',
                        'fused_to',
                    ]
                )
                
                return Response(
                    {
                        "detail": "Emenda de reparo registrada (mesma fibra)",
                        "fusion": {
                            "infrastructure_id": infra.id,
                            "tray": tray,
                            "slot": slot,
                            "fiber": (
                                f"{strand_a.tube.cable.name} "
                                f"FO{strand_a.number}"
                            ),
                            "repair": True
                        }
                    },
                    status=status.HTTP_201_CREATED,
                )

            # Permite refusão: se fibra já fusionada, desfaz automaticamente
            if strand_a.fused_to:
                old_pair = strand_a.fused_to
                old_pair.fused_to = None
                old_pair.fusion_infrastructure = None
                old_pair.fusion_tray = None
                old_pair.fusion_slot = None
                old_pair.save(
                    update_fields=[
                        'fused_to',
                        'fusion_infrastructure',
                        'fusion_tray',
                        'fusion_slot',
                    ]
                )
            
            if strand_b.fused_to:
                old_pair = strand_b.fused_to
                old_pair.fused_to = None
                old_pair.fusion_infrastructure = None
                old_pair.fusion_tray = None
                old_pair.fusion_slot = None
                old_pair.save(
                    update_fields=[
                        'fused_to',
                        'fusion_infrastructure',
                        'fusion_tray',
                        'fusion_slot',
                    ]
                )

            # Permitir fusões no mesmo cabo (sangria/reparo)
            # Validação removida: fusões intra-cabo são válidas

            # Realizar fusão bidirecional
            strand_a.fused_to = strand_b
            strand_b.fused_to = strand_a

            # Marcar localização física (ambas apontam para mesmo slot)
            strand_a.fusion_infrastructure = infra
            strand_a.fusion_tray = tray
            strand_a.fusion_slot = slot

            strand_b.fusion_infrastructure = infra
            strand_b.fusion_tray = tray
            strand_b.fusion_slot = slot

            strand_a.save(
                update_fields=[
                    'fused_to',
                    'fusion_infrastructure',
                    'fusion_tray',
                    'fusion_slot',
                ]
            )
            strand_b.save(
                update_fields=[
                    'fused_to',
                    'fusion_infrastructure',
                    'fusion_tray',
                    'fusion_slot',
                ]
            )

        return Response(
            {
                "detail": "Fusão registrada na matriz",
                "fusion": {
                    "infrastructure_id": infra.id,
                    "tray": tray,
                    "slot": slot,
                    "fiber_a": (
                        f"{strand_a.tube.cable.name} "
                        f"FO{strand_a.number}"
                    ),
                    "fiber_b": (
                        f"{strand_b.tube.cable.name} "
                        f"FO{strand_b.number}"
                    ),
                }
            },
            status=status.HTTP_201_CREATED,
        )


class DeleteFusionView(APIView):
    """
    DELETE /api/v1/fusions/<fiber_id>/

    Remove a marcação de fusão da fibra informada (e de seu par),
    liberando o slot (bandeja/slot) na matriz da CEO.

    Agora limpa a fusão bidirecional (fused_to).

    Resultado:
    - 204 No Content em sucesso
    - 404 se fibra não existe
    """

    def delete(self, request: Request, fiber_id: int) -> Response:
        try:
            strand = FiberStrand.objects.select_related(
                'fused_to'
            ).get(pk=fiber_id)
        except FiberStrand.DoesNotExist:
            return Response(
                {"detail": "Fibra não encontrada"},
                status=status.HTTP_404_NOT_FOUND,
            )

        # Se não possui fusão, retorna sucesso sem ação
        if not strand.fused_to:
            return Response(status=status.HTTP_204_NO_CONTENT)

        with transaction.atomic():
            pair = strand.fused_to

            # Limpar fusão bidirecional
            strand.fused_to = None
            strand.fusion_infrastructure = None
            strand.fusion_tray = None
            strand.fusion_slot = None

            pair.fused_to = None
            pair.fusion_infrastructure = None
            pair.fusion_tray = None
            pair.fusion_slot = None

            strand.save(
                update_fields=[
                    'fused_to',
                    'fusion_infrastructure',
                    'fusion_tray',
                    'fusion_slot',
                ]
            )
            pair.save(
                update_fields=[
                    'fused_to',
                    'fusion_infrastructure',
                    'fusion_tray',
                    'fusion_slot',
                ]
            )

        return Response(status=status.HTTP_204_NO_CONTENT)


class BoxContextView(APIView):
    """
    GET /api/v1/splice-boxes/<id>/context

    Retorna os SEGMENTOS de cabo que passam ou conectam nesta CEO,
    com estrutura completa (tubos + fibras) para seleção visual.
    
    Modelo de Segmentação:
    - Entrada: Segmentos que TERMINAM nesta CEO (end_infrastructure=ceo)
    - Saída: Segmentos que COMEÇAM nesta CEO (start_infrastructure=ceo)
    """

    def get(self, request: Request, id: int) -> Response:
        try:
            box = FiberInfrastructure.objects.get(pk=id)
        except FiberInfrastructure.DoesNotExist:
            raise Http404("Splice box não encontrada")

        from inventory.models import CableSegment
        
        # Buscar segmentos de entrada e saída
        segments_entrada = (
            CableSegment.objects.filter(end_infrastructure=box)
            .select_related('cable__profile')
            .prefetch_related('cable__tubes__strands')
        )
        
        segments_saida = (
            CableSegment.objects.filter(start_infrastructure=box)
            .select_related('cable__profile')
            .prefetch_related('cable__tubes__strands')
        )
        
        result = []
        
        # Processar segmentos de ENTRADA
        for seg in segments_entrada:
            cable = seg.cable
            result.append(
                self._serialize_segment(
                    seg, cable, box.id, port_type='oval'
                )
            )
        
        # Processar segmentos de SAÍDA
        for seg in segments_saida:
            cable = seg.cable
            result.append(
                self._serialize_segment(
                    seg, cable, box.id, port_type='round'
                )
            )
        
        # Fallback: Se não houver segmentos, tentar attachments antigos
        if not result:
            result = self._fallback_attachments(box)

        return Response(result)
    
    def _serialize_segment(
        self,
        segment: Any,
        cable: FiberCable,
        box_id: int,
        port_type: str,
    ) -> dict[str, Any]:
        """Serializa um segmento com suas fibras"""
        # Auto-gerar estrutura se necessário
        if not cable.tubes.exists() and cable.profile_id:
            try:
                cable.create_structure()
                cable.refresh_from_db()
            except Exception:
                pass
        
        tubes_data = []
        for tube in cable.tubes.all():
            strands_data = []
            for strand in tube.strands.all():
                # Incluir apenas fibras deste segmento
                if strand.segment_id != segment.id:
                    continue
                fused_here = (
                    strand.fused_to is not None
                    and strand.fusion_infrastructure_id == box_id
                )
                fused_elsewhere = (
                    strand.fused_to is not None
                    and strand.fusion_infrastructure_id
                    and strand.fusion_infrastructure_id != box_id
                )
                strands_data.append({
                    "id": strand.id,
                    "number": strand.number,
                    "absolute_number": strand.absolute_number,
                    "color": strand.color,
                    "color_hex": strand.color_hex,
                    "status": strand.status,
                    "is_fused": fused_here,  # apenas se fusão nesta caixa
                    "fused_elsewhere": fused_elsewhere,
                    "fusion_ceo": (
                        strand.fusion_infrastructure.name
                        if strand.fusion_infrastructure
                        else None
                    ),
                })
            
            if strands_data:
                tubes_data.append({
                    "id": tube.id,
                    "number": tube.number,
                    "color": tube.color,
                    "color_hex": tube.color_hex,
                    "strands": strands_data,
                })
        
        return {
            "id": cable.id,
            "name": cable.name,
            "segment_id": segment.id,
            "segment_name": segment.name,
            "segment_number": segment.segment_number,
            "tubes": tubes_data,
            "port_type": port_type,
            "is_segment": True,
            "profile_name": getattr(cable.profile, "name", None),
        }
    
    def _fallback_attachments(
        self,
        box: FiberInfrastructure,
    ) -> list[dict[str, Any]]:
        """Fallback para attachments antigos (backward compatibility)"""
        from inventory.models import InfrastructureCableAttachment
        import logging
        
        logger = logging.getLogger(__name__)
        
        attachments_qs = InfrastructureCableAttachment.objects.filter(
            infrastructure=box
        ).select_related('cable__profile')
        
        logger.info(
            "[BoxContext] Found %s attachments for CEO %s",
            attachments_qs.count(),
            box.id,
        )

        result = []
        
        for att in attachments_qs:
            cable = att.cable
            
            # Ignorar cabos marcados como ROMPIDOS (foram partidos)
            if cable.notes and '[ROMPIDO]' in cable.notes:
                logger.info(
                    f"[BoxContext] Skipping cable {cable.id} "
                    f"({cable.name}) - marked as ROMPIDO"
                )
                continue
            
            logger.info(
                f"[BoxContext] Processing cable {cable.id} "
                f"({cable.name}), profile={cable.profile_id}"
            )
            
            # Auto-gerar estrutura se perfil existe mas estrutura ausente
            if not cable.tubes.exists():
                if cable.profile_id:
                    try:
                        logger.info(
                            "[BoxContext] Creating structure for cable %s",
                            cable.id,
                        )
                        cable.create_structure()
                        cable.refresh_from_db()
                        logger.info(
                            "[BoxContext] Structure created: %s tubes",
                            cable.tubes.count(),
                        )
                    except Exception as exc:
                        logger.error(
                            "[BoxContext] Failed to create structure: %s",
                            exc,
                        )
                else:
                    logger.warning(
                        "[BoxContext] Cable %s has no profile, cannot create "
                        "structure",
                        cable.id,
                    )
                    continue  # Skip cables without profile
                    
            tubes_data = []
            for tube in cable.tubes.all():
                strands_data = []
                for strand in tube.strands.all():
                    fused_here = (
                        strand.fused_to is not None
                        and strand.fusion_infrastructure_id == box.id
                    )
                    fused_elsewhere = (
                        strand.fused_to is not None
                        and strand.fusion_infrastructure_id
                        and strand.fusion_infrastructure_id != box.id
                    )
                    virtual_id = (
                        f"{strand.id}_{att.id}" if att.id else strand.id
                    )
                    strands_data.append({
                        "id": virtual_id,
                        "real_id": strand.id,
                        "number": strand.number,
                        "absolute_number": strand.absolute_number,
                        "color": strand.color,
                        "color_hex": strand.color_hex,
                        "status": strand.status,
                        "is_fused": fused_here,
                        "fused_elsewhere": fused_elsewhere,
                        "fusion_ceo": (
                            strand.fusion_infrastructure.name
                            if strand.fusion_infrastructure
                            else None
                        ),
                    })
                
                logger.info(
                    "[BoxContext] Tube %s: %s strands",
                    tube.id,
                    len(strands_data),
                )
                
                if strands_data:  # Incluir apenas tubos com fibras disponíveis
                    tubes_data.append({
                        "id": tube.id,
                        "number": tube.number,
                        "color": tube.color,
                        "color_hex": tube.color_hex,
                        "strands": strands_data,
                    })
            
            logger.info(
                f"[BoxContext] Cable {cable.id}: "
                f"{len(tubes_data)} tubes with strands"
            )
            
            # Build direction label (Site ↔ Site/CEO)
            direction_label = cable.name  # Fallback
            direction_a = "DIREÇÃO A"  # Fallback (usado pela UI)
            direction_b = "DIREÇÃO B"

            box_display_name = box.name or f"Infra {box.id}"

            if cable.site_a and cable.site_b:
                direction_label = (
                    f"{cable.site_a.display_name} → "
                    f"{cable.site_b.display_name}"
                )
                direction_a = cable.site_a.display_name
                direction_b = cable.site_b.display_name
            elif cable.site_a:
                # Cabo chega nesta CEO a partir de site_a
                direction_label = (
                    f"{cable.site_a.display_name} → "
                    f"{box_display_name}"
                )
                direction_a = cable.site_a.display_name
                direction_b = box_display_name
            elif cable.site_b:
                # Cabo sai desta CEO em direção ao site_b
                direction_label = (
                    f"{box_display_name} → "
                    f"{cable.site_b.display_name}"
                )
                direction_a = cable.site_b.display_name
                direction_b = box_display_name
            else:
                direction_label = box_display_name or cable.name
                direction_a = box_display_name or "Direção"
                direction_b = direction_a
                    
            # Cada attachment é um item separado (2x se pass-through)
            # Adicionar com direção baseada no site de origem
            result.append({
                "id": cable.id,
                "name": cable.name,
                "tubes": tubes_data,
                "attachment_id": att.id,
                "port_type": att.port_type,
                "is_pass_through": att.is_pass_through,
                "direction": direction_a,  # Nome do site A
                "direction_label": direction_label,  # For display
                "profile_name": getattr(cable.profile, "name", None),
                "unique_id": f"{cable.id}_A_{att.id}",
            })
            
            # Se pass-through, DUPLICAR com direção do site B
            if att.is_pass_through:
                logger.info(
                    f"[BoxContext] Cable {cable.id} is pass-through, "
                    "adding second direction"
                )
                result.append({
                    "id": cable.id,
                    "name": cable.name,
                    "tubes": tubes_data,  # Mesma estrutura de tubos
                    "attachment_id": att.id,
                    "port_type": att.port_type,
                    "is_pass_through": att.is_pass_through,
                    "direction": direction_b,  # Nome do site B
                    "direction_label": direction_label,
                    "profile_name": getattr(cable.profile, "name", None),
                    "unique_id": f"{cable.id}_B_{att.id}",
                })
        
        logger.info(
            f"[BoxContext] Returning {len(result)} segments "
            "(including pass-through duplicates)"
        )
        
        # DEBUG: Show complete response
        if result:
            logger.info(
                f"[BoxContext] First segment has "
                f"{len(result[0].get('tubes', []))} tubes"
            )
        
        return result
