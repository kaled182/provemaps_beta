# pyright: reportGeneralTypeIssues=false

from __future__ import annotations

from collections import defaultdict
from typing import Any, Dict, Iterable, List, Sequence, Set

from django.db import transaction
from django.db.models import Q
from django.http import Http404
from rest_framework import status
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from inventory.models import (
    FiberCable,
    FiberFusion,
    FiberInfrastructure,
    FiberStrand,
    InfrastructureCableAttachment,
)


"""Splice matrix and context API views.

pyright: reportUnknownMemberType=false, reportUnknownVariableType=false,
    reportUnknownParameterType=false, reportUnknownAttributeUsage=false
"""


class SpliceBoxMatrixView(APIView):
    """Expose the physical fusion matrix for a splice box (CEO)."""

    def get(self, request: Request, id: int) -> Response:
        try:
            infra = FiberInfrastructure.objects.get(pk=id)
        except FiberInfrastructure.DoesNotExist as exc:
            message = "Splice box (infrastructure) não encontrada"
            raise Http404(message) from exc

        fusions = (
            FiberFusion.objects.filter(infrastructure=infra)
            .select_related(
                "fiber_a__tube__cable",
                "fiber_a__tube__cable__site_a",
                "fiber_a__tube__cable__site_b",
                "fiber_b__tube__cable",
                "fiber_b__tube__cable__site_a",
                "fiber_b__tube__cable__site_b",
            )
            .prefetch_related(
                "fiber_a__tube__cable__profile",
                "fiber_b__tube__cable__profile",
            )
        )

        matrix: Dict[str, Dict[str, Any]] = {}
        for fusion in fusions:
            if fusion.tray is None or fusion.slot is None:
                continue

            key = f"{fusion.tray}-{fusion.slot}"
            if key in matrix:
                # UniqueConstraint already protects, but guard just in case.
                continue

            is_repair = fusion.fiber_a_id == fusion.fiber_b_id
            fiber_a_payload = self._serialize_fiber(fusion.fiber_a, infra)
            if is_repair:
                fiber_b_payload = dict(fiber_a_payload)
            else:
                fiber_b_payload = self._serialize_fiber(fusion.fiber_b, infra)

            matrix[key] = {
                "tray": fusion.tray,
                "slot": fusion.slot,
                "fusion_id": fusion.pk,
                "is_repair": is_repair,
                "fiber_a": fiber_a_payload,
                "fiber_b": fiber_b_payload,
            }

        template = {
            "max_trays": infra.installed_trays or 1,
            "splices_per_tray": 24,
        }
        if infra.box_template:
            template = {
                "max_trays": infra.box_template.max_trays,
                "splices_per_tray": infra.box_template.splices_per_tray,
            }

        distance = infra.distance_from_origin or 0
        box_name = infra.name or f"CEO @ {distance:.0f}m"

        payload = {
            "infrastructure_id": infra.pk,
            "box_name": box_name,
            "template": template,
            "installed_trays": infra.installed_trays or 1,
            "matrix": matrix,
            "total_fusions": len(matrix),
        }
        return Response(payload, status=status.HTTP_200_OK)

    @staticmethod
    def _serialize_fiber(
        strand: FiberStrand,
        infra: FiberInfrastructure,
    ) -> Dict[str, Any]:
        cable = strand.tube.cable
        direction = SpliceBoxMatrixView._resolve_direction(cable, infra)

        return {
            "id": strand.pk,
            "number": strand.number,
            "absolute_number": strand.absolute_number,
            "color": strand.color,
            "color_hex": strand.color_hex,
            "color_name": strand.color,
            "cable": cable.name,
            "cable_id": cable.pk,
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
    def _resolve_direction(
        cable: FiberCable,
        infra: FiberInfrastructure,
    ) -> Dict[str, str | None]:
        box_label = infra.name or f"CEO-{infra.pk}"
        site_a = cable.site_a.display_name if cable.site_a else None
        site_b = cable.site_b.display_name if cable.site_b else None

        label = cable.name
        if site_a and site_b:
            label = f"{site_a} → {site_b}"
        elif site_a:
            label = f"{site_a} → {box_label}"
        elif site_b:
            label = f"{box_label} → {site_b}"

        remote = site_a or site_b or box_label
        return {
            "label": label,
            "remote": remote,
            "a": site_a or box_label,
            "b": site_b or box_label,
        }


class CreateFusionView(APIView):
    """Create a new `FiberFusion` entry for the given slot."""

    def post(self, request: Request) -> Response:
        data = request.data or {}
        infra_id = data.get("infrastructure_id")
        tray = data.get("tray")
        slot = data.get("slot")
        fiber_a_id = data.get("fiber_a")
        fiber_b_id = data.get("fiber_b")

        if not all([infra_id, tray, slot, fiber_a_id, fiber_b_id]):
            detail = (
                "Campos obrigatórios: infrastructure_id, tray, slot, "
                "fiber_a, fiber_b"
            )
            return Response(
                {"detail": detail},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            tray_int = int(tray)
            slot_int = int(slot)
        except (TypeError, ValueError):
            return Response(
                {"detail": "Tray e slot devem ser números inteiros"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if slot_int < 1 or slot_int > 24:
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
        if tray_int < 1 or tray_int > trays:
            return Response(
                {"detail": f"Bandeja inválida (1–{trays})"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        with transaction.atomic():
            occupied = (
                FiberFusion.objects.select_for_update()
                .filter(
                    infrastructure=infra,
                    tray=tray_int,
                    slot=slot_int,
                )
                .first()
            )
            if occupied:
                detail = (
                    f"Slot {slot_int} da Bandeja {tray_int} já está ocupado"
                )
                return Response(
                    {"detail": detail, "fusion_id": occupied.pk},
                    status=status.HTTP_409_CONFLICT,
                )

            try:
                strand_a = (
                    FiberStrand.objects.select_for_update().get(pk=fiber_a_id)
                )
            except FiberStrand.DoesNotExist:
                return Response(
                    {"detail": "Fibra A não encontrada"},
                    status=status.HTTP_404_NOT_FOUND,
                )

            if int(fiber_b_id) == strand_a.pk:
                strand_b = strand_a
            else:
                try:
                    strand_b = (
                        FiberStrand.objects.select_for_update().get(
                            pk=fiber_b_id
                        )
                    )
                except FiberStrand.DoesNotExist:
                    return Response(
                        {"detail": "Fibra B não encontrada"},
                        status=status.HTTP_404_NOT_FOUND,
                    )

            # Remover fusões apenas dentro da mesma infraestrutura
            FiberFusion.objects.filter(
                Q(fiber_a=strand_a) | Q(fiber_b=strand_a),
                infrastructure=infra,
            ).delete()
            if strand_b.pk != strand_a.pk:
                FiberFusion.objects.filter(
                    Q(fiber_a=strand_b) | Q(fiber_b=strand_b),
                    infrastructure=infra,
                ).delete()

            fusion = FiberFusion.objects.create(
                infrastructure=infra,
                tray=tray_int,
                slot=slot_int,
                fiber_a=strand_a,
                fiber_b=strand_b,
            )

        fusion_payload = {
            "id": fusion.pk,
            "infrastructure_id": infra.pk,
            "tray": tray_int,
            "slot": slot_int,
            "fiber_a": (
                f"{strand_a.tube.cable.name} FO{strand_a.number}"
            ),
            "fiber_b": (
                f"{strand_b.tube.cable.name} FO{strand_b.number}"
            ),
        }
        return Response(
            {"detail": "Fusão registrada na matriz", "fusion": fusion_payload},
            status=status.HTTP_201_CREATED,
        )


class DeleteFusionView(APIView):
    """Remove fusions scoped to the current infrastructure or by fusion id."""

    def delete(self, request: Request, fiber_id: int) -> Response:
        try:
            strand = FiberStrand.objects.get(pk=fiber_id)
        except FiberStrand.DoesNotExist:
            return Response(
                {"detail": "Fibra não encontrada"},
                status=status.HTTP_404_NOT_FOUND,
            )

        fusion_id = request.query_params.get("fusion_id")
        if fusion_id is not None:
            try:
                fusion_pk = int(fusion_id)
            except (TypeError, ValueError):
                return Response(
                    {"detail": "fusion_id inválido"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            deleted_count, _ = FiberFusion.objects.filter(
                Q(fiber_a=strand) | Q(fiber_b=strand),
                pk=fusion_pk,
            ).delete()
            if deleted_count == 0:
                return Response(status=status.HTTP_404_NOT_FOUND)
            return Response(status=status.HTTP_204_NO_CONTENT)

        infra_id_param = request.query_params.get("infrastructure_id")
        filters = Q(fiber_a=strand) | Q(fiber_b=strand)
        if infra_id_param is not None:
            try:
                infra_id = int(infra_id_param)
            except (TypeError, ValueError):
                return Response(
                    {"detail": "infrastructure_id inválido"},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            filters &= Q(infrastructure_id=infra_id)

        deleted_count, _ = FiberFusion.objects.filter(filters).delete()
        if deleted_count == 0:
            return Response(status=status.HTTP_404_NOT_FOUND)
        return Response(status=status.HTTP_204_NO_CONTENT)


class BoxContextView(APIView):
    """Return virtual segments (IN/OUT) for the requested splice box."""

    def get(self, request: Request, id: int) -> Response:
        try:
            box = FiberInfrastructure.objects.select_related("cable").get(
                pk=id
            )
        except FiberInfrastructure.DoesNotExist as exc:
            raise Http404("Splice box não encontrada") from exc

        cables = self._collect_cables(box)
        if not cables:
            return Response([], status=status.HTTP_200_OK)

        for cable in cables:
            if not cable.tubes.exists() and cable.profile_id:
                try:
                    cable.create_structure()
                    cable.refresh_from_db()
                except Exception:  # pragma: no cover - fallback only
                    pass

        fusion_lookup = self._build_fusion_lookup(self._iter_fiber_ids(cables))
        attachments = self._group_attachments(box)

        # NOVO: Construir DOIS passes - primeiro mapear todas as fibras aos seus segmentos
        segment_fiber_map_in: Dict[int, str] = {}  # Fibras do segmento IN
        segment_fiber_map_out: Dict[int, str] = {}  # Fibras do segmento OUT
        segment_fiber_map_local: Dict[int, str] = {}  # Fibras do segmento LOCAL

        # Primeiro passe: mapear fibras aos segmentos
        for cable in cables:
            timeline = self._build_timeline(cable)
            box_index = self._find_box_index(timeline, box.pk)

            if box_index is None:
                # Cabo anexado = LOCAL
                for tube in cable.tubes.all():
                    for strand in tube.strands.all():
                        segment_fiber_map_local[strand.pk] = "LOCAL"
                continue

            if box_index > 0:
                # Cabo tem entrada (IN)
                for tube in cable.tubes.all():
                    for strand in tube.strands.all():
                        segment_fiber_map_in[strand.pk] = "IN"

            if box_index < len(timeline) - 1:
                # Cabo tem saída (OUT)
                for tube in cable.tubes.all():
                    for strand in tube.strands.all():
                        segment_fiber_map_out[strand.pk] = "OUT"

        primary_render_registry: Set[int] = set()

        # Segundo passe: construir segmentos com mapeamentos corretos
        segments: List[Dict[str, Any]] = []
        for cable in cables:
            timeline = self._build_timeline(cable)
            box_index = self._find_box_index(timeline, box.pk)

            if box_index is None:
                for attachment in attachments.get(cable.pk, []):
                    segments.append(
                        self._build_attachment_segment(
                            cable=cable,
                            box=box,
                            attachment=attachment,
                            fusion_lookup=fusion_lookup,
                            segment_fiber_map=segment_fiber_map_local,
                            primary_render_registry=primary_render_registry,
                        )
                    )
                continue

            if box_index > 0:
                prev_point = timeline[box_index - 1]
                # CORRIGIDO: passar o mapa IN para que a lógica encontre o próprio segmento
                segments.append(
                    self._build_segment_payload(
                        cable=cable,
                        suffix=f"PREV_{prev_point['key']}",
                        label=f"{cable.name} [Vindo de {prev_point['name']}]",
                        direction="IN",
                        box=box,
                        fusion_lookup=fusion_lookup,
                        segment_fiber_map=segment_fiber_map_in,  # Mapa do próprio segmento IN
                        primary_render_registry=primary_render_registry,
                    )
                )

            if box_index < len(timeline) - 1:
                next_point = timeline[box_index + 1]
                # CORRIGIDO: passar o mapa OUT para que a lógica encontre o próprio segmento
                segments.append(
                    self._build_segment_payload(
                        cable=cable,
                        suffix=f"NEXT_{next_point['key']}",
                        label=f"{cable.name} [Indo para {next_point['name']}]",
                        direction="OUT",
                        box=box,
                        fusion_lookup=fusion_lookup,
                        segment_fiber_map=segment_fiber_map_out,  # Mapa do próprio segmento OUT
                        primary_render_registry=primary_render_registry,
                    )
                )

        return Response(segments, status=status.HTTP_200_OK)

    @staticmethod
    def _collect_cables(box: FiberInfrastructure) -> List[FiberCable]:
        ids: List[int] = []
        if box.cable_id:
            ids.append(box.cable_id)

        qs = (
            InfrastructureCableAttachment.objects.filter(infrastructure=box)
            .select_related("cable__site_a", "cable__site_b")
        )
        ids.extend(
            attachment.cable_id for attachment in qs if attachment.cable_id
        )

        if not ids:
            return []

        cables = list(
            FiberCable.objects.filter(id__in=set(ids))
            .select_related("site_a", "site_b")
            .prefetch_related("infrastructure_points")
            .prefetch_related("tubes__strands")
        )
        return cables

    @staticmethod
    def _iter_fiber_ids(cables: Iterable[FiberCable]) -> List[int]:
        ids: List[int] = []
        for cable in cables:
            for tube in cable.tubes.all():
                ids.extend(strand.pk for strand in tube.strands.all())
        return ids

    def _build_timeline(self, cable: FiberCable) -> List[Dict[str, Any]]:
        timeline: List[Dict[str, Any]] = []

        if cable.site_a:
            timeline.append(
                {
                    "type": "site",
                    "id": cable.site_a.pk,
                    "name": cable.site_a.display_name,
                    "dist": 0.0,
                    "key": f"site-{cable.site_a.pk}",
                }
            )

        infra_points = cable.infrastructure_points.order_by(
            "distance_from_origin"
        )
        for infra in infra_points:
            dist = infra.distance_from_origin or 0.0
            timeline.append(
                {
                    "type": "infra",
                    "id": infra.pk,
                    "name": infra.name or f"Infra {infra.pk}",
                    "dist": dist,
                    "key": f"infra-{infra.pk}",
                }
            )

        if cable.site_b:
            existing_distances = [item["dist"] for item in timeline] or [0.0]
            base_max = max(existing_distances)
            length_m = float(cable.length_km or 0) * 1000
            end_dist = max(length_m, base_max + 1.0)
            timeline.append(
                {
                    "type": "site",
                    "id": cable.site_b.pk,
                    "name": cable.site_b.display_name,
                    "dist": end_dist,
                    "key": f"site-{cable.site_b.pk}",
                }
            )

        timeline.sort(
            key=lambda item: (item["dist"], 0 if item["type"] == "site" else 1)
        )
        return timeline

    @staticmethod
    def _find_box_index(
        timeline: Sequence[Dict[str, Any]],
        box_id: int,
    ) -> int | None:
        for index, point in enumerate(timeline):
            if point["type"] == "infra" and point["id"] == box_id:
                return index
        return None

    def _build_segment_payload(
        self,
        *,
        cable: FiberCable,
        suffix: str,
        label: str,
        direction: str,
        box: FiberInfrastructure,
        fusion_lookup: Dict[int, List[FiberFusion]],
        segment_fiber_map: Dict[int, str] = None,
        primary_render_registry: Set[int] | None = None,
    ) -> Dict[str, Any]:
        return {
            "id": cable.pk,
            "virtual_id": f"{cable.pk}_{suffix}",
            "name": cable.name,
            "label": label,
            "direction": direction,
            "tubes": self._serialize_tubes_for_box(
                cable=cable,
                box=box,
                fusion_lookup=fusion_lookup,
                segment_direction=direction,  # NOVO: passa direção do segmento
                segment_fiber_map=segment_fiber_map,
                primary_render_registry=primary_render_registry,
            ),
        }

    def _build_attachment_segment(
        self,
        *,
        cable: FiberCable,
        box: FiberInfrastructure,
        attachment: InfrastructureCableAttachment,
        fusion_lookup: Dict[int, List[FiberFusion]],
        segment_fiber_map: Dict[int, str] = None,
        primary_render_registry: Set[int] | None = None,
    ) -> Dict[str, Any]:
        label = box.name or f"Infra {box.pk}"
        return {
            "id": cable.pk,
            "virtual_id": f"{cable.pk}_ATT_{attachment.pk}",
            "name": cable.name,
            "label": f"{cable.name} [Ligado a {label}]",
            "direction": "LOCAL",
            "port_type": attachment.port_type,
            "tubes": self._serialize_tubes_for_box(
                cable=cable,
                box=box,
                fusion_lookup=fusion_lookup,
                segment_direction="LOCAL",  # NOVO: anexos são sempre LOCAL
                segment_fiber_map=segment_fiber_map,
                primary_render_registry=primary_render_registry,
            ),
        }

    @staticmethod
    def _group_attachments(
        box: FiberInfrastructure,
    ) -> Dict[int, List[InfrastructureCableAttachment]]:
        grouped: Dict[
            int,
            List[InfrastructureCableAttachment],
        ] = defaultdict(list)
        qs = InfrastructureCableAttachment.objects.filter(infrastructure=box)
        for attachment in qs:
            if attachment.cable_id:
                grouped[attachment.cable_id].append(attachment)
        return grouped

    def _serialize_tubes_for_box(
        self,
        *,
        cable: FiberCable,
        box: FiberInfrastructure,
        fusion_lookup: Dict[int, List[FiberFusion]],
        segment_direction: str = None,  # NOVO: direção do segmento (IN, OUT, LOCAL)
        segment_fiber_map: Dict[int, str] = None,  # NOVO: mapa fiber_id → segment_direction
        primary_render_registry: Set[int] | None = None,
    ) -> List[Dict[str, Any]]:
        tubes_payload: List[Dict[str, Any]] = []
        for tube in cable.tubes.all():
            strands_payload: List[Dict[str, Any]] = []
            for strand in tube.strands.all():
                is_primary_render = True
                if primary_render_registry is not None:
                    if strand.pk in primary_render_registry:
                        is_primary_render = False
                    else:
                        primary_render_registry.add(strand.pk)
                fusions = fusion_lookup.get(strand.pk, [])
                fusion_payloads = [
                    self._serialize_fusion_payload(
                        strand=strand,
                        fusion=fusion,
                        current_box_id=box.pk,
                        segment_direction=segment_direction,  # NOVO: passa direção
                        segment_fiber_map=segment_fiber_map,  # NOVO: passa mapa
                    )
                    for fusion in fusions
                ]
                fusion_payloads.sort(
                    key=lambda payload: (
                        0 if payload["is_local"] else 1,
                        payload["created_at"],
                    )
                )
                primary_fusion = next(
                    (
                        payload
                        for payload in fusion_payloads
                        if payload["applies_to_segment"]
                    ),
                    fusion_payloads[0] if fusion_payloads else None,
                )
                is_fused_here = any(
                    payload["applies_to_segment"]
                    for payload in fusion_payloads
                )
                has_remote_fusion = any(
                    payload["is_remote"] for payload in fusion_payloads
                )
                is_fused_anywhere = bool(fusion_payloads)
                has_local_elsewhere = any(
                    payload["is_local"] and not payload["applies_to_segment"]
                    for payload in fusion_payloads
                )
                other_segment_direction = next(
                    (
                        payload["blocking_direction"]
                        for payload in fusion_payloads
                        if payload["is_local"]
                        and not payload["applies_to_segment"]
                        and payload.get("blocking_direction")
                    ),
                    None,
                )
                fusion_ceo = next(
                    (
                        payload["infrastructure_name"]
                        for payload in fusion_payloads
                        if payload["infrastructure_id"]
                        and payload["infrastructure_id"] != box.pk
                    ),
                    None,
                )

                strands_payload.append(
                    {
                        "id": strand.pk,
                        "number": strand.number,
                        "absolute_number": strand.absolute_number,
                        "color": strand.color,
                        "color_hex": strand.color_hex,
                        "status": strand.status,
                        "is_primary_render": is_primary_render,
                        "is_fused_here": is_fused_here,
                        "is_fused": is_fused_here,
                        "is_fused_anywhere": is_fused_anywhere,
                        "fused_elsewhere": has_remote_fusion,
                        "fused_on_other_segment": has_local_elsewhere,
                        "blocked_segment_direction": (
                            other_segment_direction
                            if has_local_elsewhere
                            else None
                        ),
                        "fusion_ceo": fusion_ceo,
                        "fusion_count": len(fusion_payloads),
                        "has_multiple_fusions": len(fusion_payloads) > 1,
                        "primary_peer_fiber_id": (
                            primary_fusion["peer_fiber_id"]
                            if primary_fusion
                            else None
                        ),
                        "primary_fusion": primary_fusion,
                        "fusions": fusion_payloads,
                        "fusion_ids": [
                            payload["id"] for payload in fusion_payloads
                        ],
                    }
                )

            tubes_payload.append(
                {
                    "id": tube.pk,
                    "number": tube.number,
                    "color": tube.color,
                    "color_hex": tube.color_hex,
                    "strands": strands_payload,
                }
            )
        return tubes_payload

    @staticmethod
    def _serialize_fusion_payload(
        *,
        strand: FiberStrand,
        fusion: FiberFusion,
        current_box_id: int,
        segment_direction: str = None,  # NOVO: direção do segmento atual (IN/OUT/LOCAL)
        segment_fiber_map: Dict[int, str] = None,  # NOVO: mapa fiber_id → segment_direction
    ) -> Dict[str, Any]:
        if fusion.fiber_a_id == strand.pk:
            peer = fusion.fiber_b
        elif fusion.fiber_b_id == strand.pk:
            peer = fusion.fiber_a
        else:  # pragma: no cover - defensive guard
            peer = None

        cable = getattr(getattr(peer, "tube", None), "cable", None)
        infrastructure = fusion.infrastructure
        
        # Lógica simplificada: fusão é "local" se foi feita nesta CEO
        # O bloqueio agora considera o papel da fibra no segmento virtual
        # (IN usa fiber_a, OUT usa fiber_b); segmentos extras seguem disponíveis
        is_local_fusion = fusion.infrastructure_id == current_box_id
        is_remote_fusion = (
            fusion.infrastructure_id is not None
            and fusion.infrastructure_id != current_box_id
        )

        fiber_role = None
        if fusion.fiber_a_id == strand.pk:
            fiber_role = "fiber_a"
        elif fusion.fiber_b_id == strand.pk:
            fiber_role = "fiber_b"

        applies_to_segment = False
        direction = segment_direction
        if direction is None and segment_fiber_map:
            direction = segment_fiber_map.get(strand.pk)

        blocking_direction = None
        if is_local_fusion:
            if direction == "IN":
                applies_to_segment = fiber_role == "fiber_a"
            elif direction == "OUT":
                applies_to_segment = fiber_role == "fiber_b"
            else:
                applies_to_segment = True

            if fiber_role == "fiber_a":
                blocking_direction = "IN"
            elif fiber_role == "fiber_b":
                blocking_direction = "OUT"

        peer_payload = (
            {
                "id": peer.pk,
                "number": peer.number,
                "absolute_number": peer.absolute_number,
                "color": peer.color,
                "color_hex": peer.color_hex,
                "cable_id": cable.pk if cable else None,
                "cable_name": cable.name if cable else None,
            }
            if peer
            else None
        )

        return {
            "id": fusion.pk,
            "infrastructure_id": (
                infrastructure.pk if infrastructure else None
            ),
            "infrastructure_name": (
                infrastructure.name if infrastructure else None
            ),
            "tray": fusion.tray,
            "slot": fusion.slot,
            "created_at": fusion.created_at.isoformat(),
            "peer": peer_payload,
            "peer_fiber_id": (
                peer_payload["id"] if peer_payload else None
            ),
            "peer_cable_id": (
                peer_payload["cable_id"] if peer_payload else None
            ),
            "peer_cable_name": (
                peer_payload["cable_name"] if peer_payload else None
            ),
            "peer_number": (
                peer_payload["number"] if peer_payload else None
            ),
            "peer_absolute_number": (
                peer_payload["absolute_number"] if peer_payload else None
            ),
            "peer_color": (
                peer_payload["color"] if peer_payload else None
            ),
            "peer_color_hex": (
                peer_payload["color_hex"] if peer_payload else None
            ),
            "is_repair": bool(
                peer_payload and peer_payload.get("id") == strand.pk
            ),
            "is_local": is_local_fusion,  # MODIFICADO: usa lógica melhorada
            "is_remote": is_remote_fusion,
            "fiber_role": fiber_role,
            "applies_to_segment": applies_to_segment,
            "blocking_direction": blocking_direction,
        }

    @staticmethod
    def _build_fusion_lookup(
        fiber_ids: Sequence[int],
    ) -> Dict[int, List[FiberFusion]]:
        if not fiber_ids:
            return {}

        fusions = (
            FiberFusion.objects.filter(
                Q(fiber_a_id__in=fiber_ids) | Q(fiber_b_id__in=fiber_ids)
            )
            .select_related(
                "infrastructure",
                "fiber_a__tube__cable",
                "fiber_b__tube__cable",
            )
            .order_by("created_at", "id")
        )

        lookup: Dict[int, List[FiberFusion]] = defaultdict(list)
        for fusion in fusions:
            lookup[fusion.fiber_a_id].append(fusion)
            lookup[fusion.fiber_b_id].append(fusion)
        return lookup
