"""core.urls_zabbix_proxy has been removed; use inventory.api.zabbix_lookup instead."""

from __future__ import annotations

from typing import NoReturn


def __getattr__(name: str) -> NoReturn:  # pragma: no cover - defensive guard
    raise RuntimeError(
        "core.urls_zabbix_proxy is no longer available. "
        "Include inventory.api.zabbix_lookup endpoints instead."
    )

