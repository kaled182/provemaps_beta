from __future__ import annotations

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from typing import Any, Dict

from .events import build_dashboard_payload

DASHBOARD_STATUS_GROUP = "dashboard_status"


def broadcast_dashboard_status(hosts_status_data: Dict[str, Any]) -> bool:
    """
    Broadcast the latest dashboard status snapshot to connected clients.

    Returns True when the message was queued successfully, False when the
    channel layer is not configured.
    """
    channel_layer = get_channel_layer()
    if channel_layer is None:
        return False

    payload = build_dashboard_payload(hosts_status_data)

    async_to_sync(channel_layer.group_send)(
        DASHBOARD_STATUS_GROUP,
        {"type": "dashboard.status", "payload": payload},
    )
    return True
