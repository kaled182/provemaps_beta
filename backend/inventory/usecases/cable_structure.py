"""Estrutura física do cabo — Cabo → Tubos loose → Fibras, cores ABNT (EV-0133).

O cabo precisa de um perfil (nº de fibras, tubos, fibras por tubo). Sem perfil, escolhe-se o
que tem o mesmo nº de fibras do grupo do cabo (ex.: «FURUKAWA AS120 12-FO» → «Cabo 12FO»);
sem grupo, a estrutura fica à espera de que alguém escolha o perfil (``needs_profile``).
"""

from __future__ import annotations

from typing import Any

from django.shortcuts import get_object_or_404

from inventory.cache.fibers import invalidate_fiber_cache
from inventory.models import FiberCable, FiberProfile
from maps_view.cache_swr import invalidate_dashboard_cache

from .devices_common import InventoryValidationError


def profile_for(cable: FiberCable) -> FiberProfile | None:
    """O perfil do cabo, ou o que corresponde ao nº de fibras do grupo dele."""
    if cable.profile_id:
        return cable.profile
    fibers = getattr(getattr(cable, "cable_group", None), "fiber_count", None)
    if not fibers:
        return None
    return FiberProfile.objects.filter(total_fibers=fibers).order_by("id").first()


def ensure_cable_structure(cable: FiberCable) -> dict[str, Any]:
    """Gera tubos e fibras se o cabo ainda não os tem. Idempotente."""
    if cable.tubes.exists():
        return {"created": False, "needs_profile": False}
    profile = profile_for(cable)
    if profile is None:
        return {"created": False, "needs_profile": True}
    if cable.profile_id != profile.pk:
        cable.profile = profile
        cable.save(update_fields=["profile"])
    created = cable.create_structure()
    if created:
        invalidate_fiber_cache()
        invalidate_dashboard_cache()
    return {"created": created, "needs_profile": False}


def available_profiles() -> list[dict[str, Any]]:
    return [
        {"id": p.pk, "name": p.name, "total_fibers": p.total_fibers}
        for p in FiberProfile.objects.order_by("total_fibers", "id")
    ]


def set_cable_profile(cable_id: int, profile_id: int) -> dict[str, Any]:
    """Escolhe o perfil de um cabo sem estrutura (ex.: sem grupo) e gera-a."""
    cable = get_object_or_404(FiberCable, pk=cable_id)
    if cable.tubes.exists():
        raise InventoryValidationError("o cabo já tem a estrutura gerada; o perfil não se troca")
    cable.profile = get_object_or_404(FiberProfile, pk=profile_id)
    cable.save(update_fields=["profile"])
    return ensure_cable_structure(cable)
