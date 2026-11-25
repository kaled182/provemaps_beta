"""Ocupação de um cabo a partir das fibras cadastradas (EV-0061).

Sem fibras cadastradas a ocupação é desconhecida (`None`) — nunca 0 %: a barra do
inventário mostrava 0 % inventado porque lia um campo que ninguém produzia.
"""

from __future__ import annotations

from typing import Any

from django.db.models import Count, Q

USED_STATUSES = ("lit", "reserved")

# EV-0133: «em uso» = iluminada/reservada, ligada a uma porta, ou emendada numa CEO.
_USED = (
    Q(tubes__strands__status__in=USED_STATUSES)
    | Q(tubes__strands__connected_device_port__isnull=False)
    | Q(tubes__strands__fusions_as_a__isnull=False)
    | Q(tubes__strands__fusions_as_b__isnull=False)
    # EV-0142: fibra ligada a um splitter (entrada ou saída de porta) também está usada
    | Q(tubes__strands__splitter_inputs__isnull=False)
    | Q(tubes__strands__splitter_outputs__isnull=False)
)

# Anotações para um queryset de FiberCable (uma consulta para a lista toda).
OCCUPANCY_ANNOTATIONS = {
    "strands_registered": Count("tubes__strands", distinct=True),
    "strands_used": Count("tubes__strands", filter=_USED, distinct=True),
    "strands_free": Count("tubes__strands", filter=Q(tubes__strands__status="dark"), distinct=True),
    "strands_broken": Count(
        "tubes__strands", filter=Q(tubes__strands__status="broken"), distinct=True
    ),
}


def occupancy_from_counts(
    registered: int, used: int, free: int, broken: int
) -> dict[str, Any] | None:
    if not registered:
        return None
    return {"registered": registered, "used": used, "free": free, "broken": broken}
