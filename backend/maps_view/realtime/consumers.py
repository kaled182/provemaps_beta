from __future__ import annotations

import logging

from channels.generic.websocket import AsyncJsonWebsocketConsumer

from .publisher import DASHBOARD_STATUS_GROUP

logger = logging.getLogger(__name__)


class DashboardStatusConsumer(AsyncJsonWebsocketConsumer):
    """WebSocket consumer that streams dashboard status updates in real time."""

    async def connect(self):
        user = self.scope.get("user")
        if not user or not user.is_authenticated:
            logger.warning(
                "Realtime websocket denied: anonymous user",
                extra={
                    "remote_addr": self.scope.get("client"),
                    "path": self.scope.get("path"),
                },
            )
            await self.close(code=4401)
            return

        try:
            await self.channel_layer.group_add(DASHBOARD_STATUS_GROUP, self.channel_name)
        except Exception as exc:  # pragma: no cover - defensive logging
            logger.exception(
                "Failed to join realtime group",
                extra={
                    "channel_name": self.channel_name,
                    "path": self.scope.get("path"),
                },
            )
            await self.close(code=1011)
            return

        logger.info(
            "Realtime websocket connected",
            extra={
                "remote_addr": self.scope.get("client"),
                "user": getattr(user, "username", None),
            },
        )
        await self.accept()

    async def disconnect(self, code):
        logger.info(
            "Realtime websocket disconnected",
            extra={
                "code": code,
                "remote_addr": self.scope.get("client"),
            },
        )
        await self.channel_layer.group_discard(DASHBOARD_STATUS_GROUP, self.channel_name)

    async def receive_json(self, content, **kwargs):
        # No-op: clients currently receive push-only updates.
        return

    async def dashboard_status(self, event):
        await self.send_json(event.get("payload", {}))
