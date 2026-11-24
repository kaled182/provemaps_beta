"""Regras do ecrã «Monitoramento GPON» (EV-0095) — puras, sem Django.

Sinal, queda coletiva, severidade de PON e de ONU, ocupação. Os limiares e as capacidades
chegam por parâmetro (vêm da configuração de runtime, nunca de constantes aqui).
"""

from __future__ import annotations

from collections.abc import Iterable
from datetime import datetime

from .parsers import REASON_DYING_GASP, REASON_LOS, STATUS_OFFLINE, STATUS_ONLINE, STATUS_UNKNOWN

SIGNAL_NORMAL = "normal"
SIGNAL_WARNING = "warning"
SIGNAL_CRITICAL = "critical"

SEVERITY_NORMAL = "normal"
SEVERITY_WARNING = "warning"
SEVERITY_CRITICAL = "critical"

COLLECTIVE_DROP_MIN_ONUS = 3
COLLECTIVE_DROP_WINDOW_SECONDS = 600
PON_LOS_CRITICAL = 3
OCCUPANCY_WARNING_PCT = 85.0


def signal_dbm(rx_onu_dbm: float | None, rx_olt_dbm: float | None) -> float | None:
    """O RX que conta: na ONU se houver, senão na OLT."""
    return rx_onu_dbm if rx_onu_dbm is not None else rx_olt_dbm


def classify_signal(rx: float | None, warning: float, critical: float) -> str | None:
    """normal: rx > warning; warning: critical ≤ rx ≤ warning; critical: rx < critical."""
    if rx is None:
        return None
    if rx < critical:
        return SIGNAL_CRITICAL
    if rx <= warning:
        return SIGNAL_WARNING
    return SIGNAL_NORMAL


def is_collective_drop(
    times: Iterable[datetime],
    *,
    min_count: int = COLLECTIVE_DROP_MIN_ONUS,
    window_seconds: int = COLLECTIVE_DROP_WINDOW_SECONDS,
) -> bool:
    """≥ ``min_count`` quedas (instantes OBSERVADOS) dentro de uma janela de ``window_seconds``."""
    ordered = sorted(times)
    if len(ordered) < min_count:
        return False
    span = min_count - 1
    return any(
        (ordered[i + span] - ordered[i]).total_seconds() <= window_seconds
        for i in range(len(ordered) - span)
    )


def occupancy_pct(provisioned: int, capacity: int) -> float | None:
    if capacity <= 0:
        return None
    return round(provisioned / capacity * 100, 1)


def pon_severity(
    *,
    collective_drop: bool,
    los: int,
    status: str,
    signal_warning: int,
    signal_critical: int,
    occupancy: float | None,
) -> str:
    if collective_drop or los >= PON_LOS_CRITICAL or status == "down":
        return SEVERITY_CRITICAL
    if signal_warning + signal_critical > 0 or (
        occupancy is not None and occupancy > OCCUPANCY_WARNING_PCT
    ):
        return SEVERITY_WARNING
    return SEVERITY_NORMAL


def onu_severity_rank(status: str, reason: str | None, signal: str | None) -> int:
    """0 los · 1 sinal crítico · 2 sinal atenção · 3 dying_gasp · 4 offline · 5 unknown · 6 ok."""
    if status == STATUS_OFFLINE and reason == REASON_LOS:
        return 0
    if signal == SIGNAL_CRITICAL:
        return 1
    if signal == SIGNAL_WARNING:
        return 2
    if status == STATUS_OFFLINE and reason == REASON_DYING_GASP:
        return 3
    if status == STATUS_OFFLINE:
        return 4
    if status == STATUS_UNKNOWN or status != STATUS_ONLINE:
        return 5
    return 6
