"""Pontas da fibra (EV-0134): estado de cada fibra e «Conectar a porta» no Site A / Site B.

``FiberStrand.connected_device_port`` é a ponta do Site A e ``connected_device_port_b`` a do B.
Uma porta liga-se a uma só ponta de uma só fibra (é um cordão no DIO/equipamento).
"""

from __future__ import annotations

from typing import Any

from django.db.models import Q
from django.shortcuts import get_object_or_404

from inventory.cache.fibers import invalidate_fiber_cache
from inventory.models import FiberCable, FiberStrand, OtdrAlert, Port, Site
from maps_view.cache_swr import invalidate_dashboard_cache

from .devices_common import InventoryValidationError

ENDS = ("a", "b")
# Estado mostrado no diagrama (prioridade nesta ordem)
STATE_BROKEN, STATE_LIT, STATE_FUSED, STATE_FREE = "broken", "lit", "fused", "free"


def end_site(cable: FiberCable, end: str) -> Site | None:
    site = cable.site_a if end == "a" else cable.site_b
    if site is not None:
        return site
    port = cable.origin_port if end == "a" else cable.destination_port
    return getattr(getattr(port, "device", None), "site", None)


def strand_state(strand: FiberStrand, *, cable_broken: bool) -> str:
    """Rompida (estado manual ou rompimento OTDR ativo no cabo — um corte apanha o cabo todo) >
    iluminada (porta ligada ou estado «lit») > fusionada (emendada numa CEO) > livre."""
    if cable_broken or strand.status == FiberStrand.STATUS_BROKEN:
        return STATE_BROKEN
    if (
        strand.status == FiberStrand.STATUS_LIT
        or strand.connected_device_port_id
        or strand.connected_device_port_b_id
    ):
        return STATE_LIT
    if strand.fusions_as_a.exists() or strand.fusions_as_b.exists():
        return STATE_FUSED
    return STATE_FREE


def active_otdr(cable: FiberCable) -> dict[str, Any] | None:
    alert = (
        OtdrAlert.objects.filter(cable=cable, cleared_at__isnull=True)
        .order_by("-created_at")
        .first()
    )
    if alert is None:
        return None
    result = alert.result or {}
    return {
        "id": alert.pk,
        "status": alert.status,
        "map_distance_m": result.get("map_distance_m"),
        "origin_name": (result.get("origin") or {}).get("name"),
    }


def _used_ports(port_ids: list[int]) -> dict[int, dict[str, Any]]:
    """porta → a fibra/ponta que a usa (qualquer cabo)."""
    used: dict[int, dict[str, Any]] = {}
    qs = FiberStrand.objects.filter(
        Q(connected_device_port_id__in=port_ids) | Q(connected_device_port_b_id__in=port_ids)
    ).select_related("tube__cable")
    for s in qs:
        for end, pid in (("a", s.connected_device_port_id), ("b", s.connected_device_port_b_id)):
            if pid in port_ids:
                used[pid] = {
                    "strand_id": s.pk,
                    "cable_name": s.tube.cable.name,
                    "absolute_number": s.absolute_number,
                    "end": end,
                }
    return used


def site_ports(site: Site) -> dict[str, Any]:
    """Equipamentos do site com as portas e quem as usa (fibra/cabo/ponta)."""
    ports = list(
        Port.objects.filter(device__site=site)
        .select_related("device")
        .order_by("device__name", "name")
        .only("id", "name", "device__id", "device__name")
    )
    used = _used_ports([p.pk for p in ports])
    devices: dict[int, dict[str, Any]] = {}
    for p in ports:
        dev = devices.setdefault(
            p.device_id, {"id": p.device_id, "name": p.device.name, "ports": []}
        )
        dev["ports"].append({"id": p.pk, "name": p.name, "used_by": used.get(p.pk)})
    return {"site_id": site.pk, "site_name": site.display_name, "devices": list(devices.values())}


def cable_ends(cable: FiberCable) -> dict[str, Any]:
    """Sites das duas pontas, com os equipamentos e as portas (e quem as usa)."""
    out: dict[str, Any] = {}
    for end in ENDS:
        site = end_site(cable, end)
        out[end] = (
            site_ports(site)
            if site is not None
            else {"site_id": None, "site_name": None, "devices": []}
        )
        # EV-0135: ponta numa CEO (cabo derivado) — não há porta, a emenda é na caixa
        ceo = cable.origin_infrastructure if end == "a" else cable.destination_infrastructure
        out[end]["ceo_name"] = (ceo.name or f"CEO #{ceo.pk}") if ceo is not None else None
    return out


def connect_strand_port(
    cable_id: int, strand_id: int, *, end: str, port_id: int | None
) -> dict[str, Any]:
    """Liga (ou desliga, com ``port_id`` None) a ponta ``end`` da fibra a uma porta do site dessa ponta."""
    if end not in ENDS:
        raise InventoryValidationError("ponta deve ser «a» ou «b»")
    cable = get_object_or_404(
        FiberCable.objects.select_related(
            "site_a", "site_b", "origin_port__device", "destination_port__device"
        ),
        pk=cable_id,
    )
    strand = get_object_or_404(FiberStrand, pk=strand_id, tube__cable=cable)
    field = "connected_device_port" if end == "a" else "connected_device_port_b"
    port = None
    if port_id is not None:
        port = get_object_or_404(Port.objects.select_related("device"), pk=port_id)
        site = end_site(cable, end)
        if site is None or port.device.site_id != site.pk:
            raise InventoryValidationError(
                f"a porta tem de ser de um equipamento do site da ponta {end.upper()}"
                + (f" ({site.display_name})" if site else " (o cabo não tem site nessa ponta)")
            )
        busy = (
            FiberStrand.objects.filter(
                Q(connected_device_port=port) | Q(connected_device_port_b=port)
            )
            .exclude(pk=strand.pk)
            .select_related("tube__cable")
            .first()
        )
        if busy is not None:
            raise InventoryValidationError(
                f"a porta {port.name} já está ligada à fibra {busy.absolute_number} do cabo {busy.tube.cable.name}"
            )
        other = "connected_device_port_b" if end == "a" else "connected_device_port"
        if getattr(strand, f"{other}_id") == port.pk:
            raise InventoryValidationError("a mesma porta não pode estar nas duas pontas da fibra")
    setattr(strand, field, port)
    strand.save(update_fields=[field])
    invalidate_fiber_cache()
    invalidate_dashboard_cache()
    return {
        "strand_id": strand.pk,
        "end": end,
        "port": (
            None
            if port is None
            else {"id": port.pk, "name": port.name, "device_name": port.device.name}
        ),
        "state": strand_state(strand, cable_broken=active_otdr(cable) is not None),
    }
