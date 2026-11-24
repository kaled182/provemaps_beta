"""Aplicação de um snapshot óptico a uma porta (regra única da coleta e do refresh).

EV-0082/EV-0088: `last_optical_check` é um só para RX e TX. Só se grava uma ponta com
leitura válida (o snapshot só traz `rx_dbm`/`tx_dbm` quando válida); quando uma ponta é
gravada, a outra sem leitura válida — tenha ou não chave — passa a ``None``, para o valor
antigo não ficar sob a hora nova. Sem nenhuma leitura válida nada muda.
"""

from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime
from typing import Any


def apply_optical_snapshot(port: Any, snapshot: Mapping[str, Any], now: datetime) -> list[str]:
    """Aplica o snapshot a ``port`` (em memória) e devolve os ``update_fields``.

    Lista vazia = nada a gravar (o chamador não deve fazer ``save``).
    """
    rx_dbm = snapshot.get("rx_dbm")
    tx_dbm = snapshot.get("tx_dbm")
    if rx_dbm is None and tx_dbm is None:
        return []

    update_fields: list[str] = []
    for field, value in (("last_rx_power", rx_dbm), ("last_tx_power", tx_dbm)):
        if value is not None:
            setattr(port, field, value)
            update_fields.append(field)
        elif getattr(port, field) is not None:
            setattr(port, field, None)
            update_fields.append(field)
    port.last_optical_check = now
    update_fields.append("last_optical_check")
    return update_fields
