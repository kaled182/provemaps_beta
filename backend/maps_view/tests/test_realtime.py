"""Tests for maps_view.realtime — events, publisher."""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from django.test import TestCase


# ---------------------------------------------------------------------------
# events
# ---------------------------------------------------------------------------

class BuildDashboardPayloadTests(TestCase):
    def test_returns_correct_structure(self):
        from maps_view.realtime.events import build_dashboard_payload
        data = {
            "hosts_summary": {"total": 10, "up": 8},
            "hosts_status": [{"id": 1, "status": "up"}],
        }
        payload = build_dashboard_payload(data)
        self.assertEqual(payload["event"], "dashboard.status")
        self.assertEqual(payload["version"], 1)
        self.assertIn("timestamp", payload)
        self.assertEqual(payload["data"]["summary"]["total"], 10)
        self.assertEqual(len(payload["data"]["hosts"]), 1)

    def test_empty_input(self):
        from maps_view.realtime.events import build_dashboard_payload
        payload = build_dashboard_payload({})
        self.assertEqual(payload["data"]["summary"], {})
        self.assertEqual(payload["data"]["hosts"], [])

    def test_timestamp_is_iso_format(self):
        from maps_view.realtime.events import build_dashboard_payload
        payload = build_dashboard_payload({})
        # Should not raise when parsed
        from datetime import datetime
        datetime.fromisoformat(payload["timestamp"].replace("Z", "+00:00"))


# ---------------------------------------------------------------------------
# publisher
# ---------------------------------------------------------------------------

class BroadcastDashboardStatusTests(TestCase):
    def test_returns_false_when_no_channel_layer(self):
        from maps_view.realtime.publisher import broadcast_dashboard_status
        with patch(
            "maps_view.realtime.publisher.get_channel_layer",
            return_value=None,
        ):
            result = broadcast_dashboard_status({"hosts_status": []})
        self.assertFalse(result)

    def test_broadcasts_successfully(self):
        from maps_view.realtime.publisher import broadcast_dashboard_status
        mock_layer = MagicMock()
        with patch(
            "maps_view.realtime.publisher.get_channel_layer",
            return_value=mock_layer,
        ), patch(
            "maps_view.realtime.publisher.async_to_sync",
            return_value=lambda *a, **kw: None,
        ):
            result = broadcast_dashboard_status(
                {"hosts_summary": {}, "hosts_status": []}
            )
        self.assertTrue(result)

    def test_calls_group_send_with_correct_type(self):
        from maps_view.realtime.publisher import (
            broadcast_dashboard_status,
            DASHBOARD_STATUS_GROUP,
        )
        mock_layer = MagicMock()
        captured = {}

        def fake_group_send(group, message):
            captured["group"] = group
            captured["message"] = message

        with patch(
            "maps_view.realtime.publisher.get_channel_layer",
            return_value=mock_layer,
        ), patch(
            "maps_view.realtime.publisher.async_to_sync",
            return_value=fake_group_send,
        ):
            broadcast_dashboard_status({"hosts_summary": {}, "hosts_status": []})

        self.assertEqual(captured["group"], DASHBOARD_STATUS_GROUP)
        self.assertEqual(captured["message"]["type"], "dashboard.status")


class BroadcastCableStatusTests(TestCase):
    def test_returns_false_when_no_channel_layer(self):
        from maps_view.realtime.publisher import broadcast_cable_status_update
        with patch(
            "maps_view.realtime.publisher.get_channel_layer",
            return_value=None,
        ):
            result = broadcast_cable_status_update([])
        self.assertFalse(result)

    def test_broadcasts_cable_updates(self):
        from maps_view.realtime.publisher import broadcast_cable_status_update
        mock_layer = MagicMock()
        with patch(
            "maps_view.realtime.publisher.get_channel_layer",
            return_value=mock_layer,
        ), patch(
            "maps_view.realtime.publisher.async_to_sync",
            return_value=lambda *a, **kw: None,
        ):
            result = broadcast_cable_status_update(
                [{"cable_id": 1, "status": "ok"}]
            )
        self.assertTrue(result)

    def test_cable_broadcast_includes_timestamp(self):
        from maps_view.realtime.publisher import (
            broadcast_cable_status_update,
            CABLE_STATUS_GROUP,
        )
        captured = {}

        def fake_group_send(group, message):
            captured["group"] = group
            captured["message"] = message

        mock_layer = MagicMock()
        with patch(
            "maps_view.realtime.publisher.get_channel_layer",
            return_value=mock_layer,
        ), patch(
            "maps_view.realtime.publisher.async_to_sync",
            return_value=fake_group_send,
        ):
            broadcast_cable_status_update([{"cable_id": 99}])

        self.assertEqual(captured["group"], CABLE_STATUS_GROUP)
        payload = captured["message"]["payload"]
        self.assertIn("timestamp", payload)
        self.assertIn("cables", payload)
