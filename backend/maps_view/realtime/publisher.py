from __future__ import annotations

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from typing import Any, Dict, List

from .events import build_dashboard_payload

DASHBOARD_STATUS_GROUP = "dashboard_status"
CABLE_STATUS_GROUP = "cable_status"


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


def broadcast_cable_status_update(cable_updates: List[Dict[str, Any]]) -> bool:
    """
    Broadcast cable operational status updates to connected clients.
    
    Args:
        cable_updates: List of cable status dicts with keys:
            - cable_id
            - status
            - origin_optical
            - destination_optical
            - etc.
    
    Returns:
        True if message was queued, False if channel layer unavailable
    """
    channel_layer = get_channel_layer()
    if channel_layer is None:
        return False
    
    payload = {
        "type": "cable_status_update",
        "cables": cable_updates,
        "timestamp": __import__('time').time(),
    }
    
    async_to_sync(channel_layer.group_send)(
        CABLE_STATUS_GROUP,
        {"type": "cable.status", "payload": payload},
    )
    return True
