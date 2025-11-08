from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict


def build_dashboard_payload(hosts_status_data: Dict[str, Any]) -> Dict[str, Any]:
    """Return a normalized payload for dashboard status broadcasts."""
    return {
        "event": "dashboard.status",
        "version": 1,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "data": {
            "summary": hosts_status_data.get("hosts_summary", {}),
            "hosts": hosts_status_data.get("hosts_status", []),
        },
    }
