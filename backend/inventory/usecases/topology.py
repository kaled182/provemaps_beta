"""Topologia esquemática da rede (EV-0060, ADR 0009): POPs e enlaces entre eles.

O site de cada ponta vem do equipamento da porta (em produção `site_a`/`site_b`
estão vazios); `site_a`/`site_b` só entram como reserva. O estado de cada enlace
é o do agregado óptico (EV-0057). Capacidade: `fiber_count` do grupo do cabo;
ocupação só se houver fibras cadastradas — senão `null` (nunca 0 inventado).
"""

from __future__ import annotations

from collections import Counter
from typing import Any

from inventory.domain.strands import USED_STATUSES, occupancy_from_counts
from inventory.models import FiberCable, FiberStrand
from inventory.usecases.fibers import list_cables_optical_summary


def _end_site(port, fallback):
    device = getattr(port, "device", None) if port else None
    site = getattr(device, "site", None) if device else None
    return site or fallback


def _site_node(site) -> dict[str, Any]:
    lat = float(site.latitude) if site.latitude is not None else None
    lng = float(site.longitude) if site.longitude is not None else None
    return {"id": site.id, "name": site.display_name, "lat": lat, "lng": lng}


def build_topology() -> dict[str, Any]:
    """{"nodes": [...], "edges": [...], "unplaced": [...], "strands_registered": int}

    `edges` liga dois sites distintos com coordenadas; um cabo cujas pontas caem no
    mesmo site, ou sem site/coordenadas, vai para `unplaced` com o motivo.
    """
    cables = (
        FiberCable.objects.filter(parent_cable__isnull=True)
        .select_related(
            "origin_port__device__site",
            "destination_port__device__site",
            "site_a",
            "site_b",
            "cable_group",
        )
        .order_by("name")
    )
    health = {c["id"]: c["health"] for c in list_cables_optical_summary()["cables"]}

    strands = Counter(
        FiberStrand.objects.filter(tube__cable__parent_cable__isnull=True).values_list(
            "tube__cable_id", "status"
        )
    )
    per_cable: dict[int, dict[str, int]] = {}
    for (cable_id, status), n in strands.items():
        per_cable.setdefault(cable_id, {})[status] = n

    nodes: dict[int, dict[str, Any]] = {}
    edges: list[dict[str, Any]] = []
    unplaced: list[dict[str, Any]] = []

    for cable in cables:
        a = _end_site(cable.origin_port, cable.site_a)
        b = _end_site(cable.destination_port, cable.site_b)
        group = getattr(cable, "cable_group", None)
        counts = per_cable.get(cable.id) or {}
        occupancy = occupancy_from_counts(
            sum(counts.values()),
            sum(counts.get(st, 0) for st in USED_STATUSES),
            counts.get("dark", 0),
            counts.get("broken", 0),
        )
        item = {
            "id": cable.id,
            "name": cable.name,
            "health": health.get(cable.id, "unknown"),
            "length_km": float(cable.length_km) if cable.length_km is not None else None,
            "fiber_count": getattr(group, "fiber_count", None),
            "occupancy": occupancy,
        }
        if not a or not b:
            unplaced.append({**item, "reason": "sem site numa das pontas"})
            continue
        if a.id == b.id:
            unplaced.append({**item, "reason": f"as duas pontas no mesmo site ({a.display_name})"})
            continue
        if None in (a.latitude, a.longitude, b.latitude, b.longitude):
            unplaced.append({**item, "reason": "site sem coordenadas"})
            continue
        nodes.setdefault(a.id, _site_node(a))
        nodes.setdefault(b.id, _site_node(b))
        edges.append({**item, "source": a.id, "target": b.id})

    return {
        "nodes": sorted(nodes.values(), key=lambda n: n["name"] or ""),
        "edges": edges,
        "unplaced": unplaced,
        "strands_registered": sum(strands.values()),
    }
