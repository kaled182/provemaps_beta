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
            .select_related('tube__cable', 'fused_to__tube__cable')
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
                is_repair = (pair is None)
                matrix_data[key] = {
                    "tray": fiber.fusion_tray,
                    "slot": fiber.fusion_slot,
                    "is_repair": is_repair,
                    "fiber_a": {
                        "id": fiber.id,
                        "number": fiber.number,
                        "color": fiber.color,
                        "color_hex": fiber.color_hex,
                        "cable": fiber.tube.cable.name,
                        "cable_id": fiber.tube.cable.id,
                    },
                    "fiber_b": (
                        {
                            # Segunda fibra (ou reparo) - linhas quebradas
                            "id": (
                                fiber.id if is_repair else (
                                    pair.id if pair else None
                                )
                            ),
                            "number": (
                                fiber.number if is_repair else (
                                    pair.number if pair else None
                                )
                            ),
                            "color": (
                                fiber.color if is_repair else (
                                    pair.color if pair else None
                                )
                            ),
                            "color_hex": (
                                fiber.color_hex if is_repair else (
                                    pair.color_hex if pair else "#cccccc"
                                )
                            ),
                            "cable": (
                                fiber.tube.cable.name if is_repair else (
                                    pair.tube.cable.name if pair else "?"
                                )
                            ),
                            "cable_id": (
                                fiber.tube.cable.id if is_repair else (
                                    pair.tube.cable.id if pair else None
                                )
                            ),
                        }
                        if (is_repair or pair)
                        else None
                    )
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
    
    def _fallback_attachments(self, box: FiberInfrastructure) -> list[dict[str, Any]]:
        """Fallback para attachments antigos (backward compatibility)"""
        from inventory.models import InfrastructureCableAttachment
        
        attachments_qs = InfrastructureCableAttachment.objects.filter(
            infrastructure=box
        ).select_related('cable')

        result = []
        
        for att in attachments_qs:
            cable = att.cable
            
            # Auto-gerar estrutura se perfil existe mas estrutura ausente
            if not cable.tubes.exists() and cable.profile_id:
                try:
                    cable.create_structure()
                    cable.refresh_from_db()
                except Exception:  # pragma: no cover - geração best-effort
                    pass
                    
            tubes_data = []
            for tube in cable.tubes.all():
                strands_data = []
                for strand in tube.strands.all():
                    fused_here = strand.fused_to is not None and strand.fusion_infrastructure_id == box.id
                    fused_elsewhere = strand.fused_to is not None and strand.fusion_infrastructure_id and strand.fusion_infrastructure_id != box.id
                    virtual_id = f"{strand.id}_{att.id}" if att.id else strand.id
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
                        "fusion_ceo": strand.fusion_infrastructure.name if strand.fusion_infrastructure else None,
                    })
                
                if strands_data:  # Incluir apenas tubos com fibras disponíveis
                    tubes_data.append({
                        "id": tube.id,
                        "number": tube.number,
                        "color": tube.color,
                        "color_hex": tube.color_hex,
                        "strands": strands_data,
                    })
                    
            # Cada attachment é um item separado (permite mesmo cabo aparecer 2x)
            result.append({
                "id": cable.id,
                "name": cable.name,
                "tubes": tubes_data,
                "attachment_id": att.id,  # ID único do attachment
                "port_type": att.port_type,
                "is_pass_through": att.is_pass_through,
                "profile_name": getattr(cable.profile, "name", None),
            })

        # Se não houver anexações explícitas, usar o cabo "proprietário" da CEO
        if not result and box.cable_id:
            cable = FiberCable.objects.get(pk=box.cable_id)
            
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
                    fused_here = strand.fused_to is not None and strand.fusion_infrastructure_id == box.id
                    fused_elsewhere = strand.fused_to is not None and strand.fusion_infrastructure_id and strand.fusion_infrastructure_id != box.id
                    strands_data.append({
                        "id": strand.id,
                        "real_id": strand.id,
                        "number": strand.number,
                        "absolute_number": strand.absolute_number,
                        "color": strand.color,
                        "color_hex": strand.color_hex,
                        "status": strand.status,
                        "is_fused": fused_here,
                        "fused_elsewhere": fused_elsewhere,
                        "fusion_ceo": strand.fusion_infrastructure.name if strand.fusion_infrastructure else None,
                    })
                
                if strands_data:
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
                "attachment_id": None,
                "port_type": "owner",
                "is_pass_through": False,
                "profile_name": getattr(cable.profile, "name", None),
            })
        
            return result
