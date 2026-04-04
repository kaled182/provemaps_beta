"""Tests for core.views_api (frontend_config) and core routing helpers."""
from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import pytest
from django.test import RequestFactory, TestCase, override_settings


class FrontendConfigViewTests(TestCase):
    """Tests for core.views_api.frontend_config."""

    def setUp(self):
        self.factory = RequestFactory()

    def _mock_config(self, **kwargs):
        cfg = MagicMock()
        cfg.map_provider = kwargs.get("map_provider", "google")
        cfg.google_maps_api_key = kwargs.get("google_maps_api_key", "AIza-test")
        cfg.mapbox_token = kwargs.get("mapbox_token", "pk.test")
        cfg.esri_api_key = kwargs.get("esri_api_key", "")
        cfg.map_default_zoom = kwargs.get("map_default_zoom", 12)
        cfg.map_default_lat = kwargs.get("map_default_lat", "-15.78")
        cfg.map_default_lng = kwargs.get("map_default_lng", "-47.93")
        cfg.map_type = kwargs.get("map_type", "terrain")
        cfg.map_language = kwargs.get("map_language", "pt-BR")
        cfg.map_theme = kwargs.get("map_theme", "light")
        cfg.enable_street_view = kwargs.get("enable_street_view", True)
        cfg.enable_traffic = kwargs.get("enable_traffic", False)
        cfg.map_styles = kwargs.get("map_styles", "")
        cfg.mapbox_style = kwargs.get("mapbox_style", "streets-v12")
        cfg.mapbox_custom_style = kwargs.get("mapbox_custom_style", "")
        cfg.mapbox_enable_3d = kwargs.get("mapbox_enable_3d", False)
        cfg.esri_basemap = kwargs.get("esri_basemap", "topo-vector")
        cfg.enable_map_clustering = kwargs.get("enable_map_clustering", True)
        cfg.enable_drawing_tools = kwargs.get("enable_drawing_tools", True)
        cfg.enable_fullscreen = kwargs.get("enable_fullscreen", True)
        return cfg

    def test_returns_200(self):
        from core.views_api import frontend_config
        request = self.factory.get("/api/frontend-config/")
        with patch(
            "core.views_api.runtime_settings.get_runtime_config",
            return_value=self._mock_config(),
        ):
            response = frontend_config(request)
        self.assertEqual(response.status_code, 200)

    def test_response_includes_map_provider(self):
        from core.views_api import frontend_config
        request = self.factory.get("/api/frontend-config/")
        with patch(
            "core.views_api.runtime_settings.get_runtime_config",
            return_value=self._mock_config(map_provider="mapbox"),
        ):
            response = frontend_config(request)
        data = json.loads(response.content)
        self.assertEqual(data["mapProvider"], "mapbox")

    def test_response_includes_map_keys(self):
        from core.views_api import frontend_config
        request = self.factory.get("/api/frontend-config/")
        with patch(
            "core.views_api.runtime_settings.get_runtime_config",
            return_value=self._mock_config(google_maps_api_key="test-key"),
        ):
            response = frontend_config(request)
        data = json.loads(response.content)
        self.assertIn("googleMapsApiKey", data)
        self.assertIn("mapboxToken", data)

    def test_response_includes_lat_lng(self):
        from core.views_api import frontend_config
        request = self.factory.get("/api/frontend-config/")
        with patch(
            "core.views_api.runtime_settings.get_runtime_config",
            return_value=self._mock_config(),
        ):
            response = frontend_config(request)
        data = json.loads(response.content)
        self.assertIn("mapDefaultLat", data)
        self.assertIn("mapDefaultLng", data)
        self.assertIsInstance(data["mapDefaultLat"], float)

    def test_lat_lng_defaults_when_none(self):
        from core.views_api import frontend_config
        request = self.factory.get("/api/frontend-config/")
        cfg = self._mock_config()
        cfg.map_default_lat = None
        cfg.map_default_lng = None
        with patch(
            "core.views_api.runtime_settings.get_runtime_config",
            return_value=cfg,
        ):
            response = frontend_config(request)
        data = json.loads(response.content)
        self.assertEqual(data["mapDefaultLat"], -15.7801)
        self.assertEqual(data["mapDefaultLng"], -47.9292)

    def test_only_get_allowed(self):
        from core.views_api import frontend_config
        request = self.factory.post("/api/frontend-config/")
        with patch(
            "core.views_api.runtime_settings.get_runtime_config",
            return_value=self._mock_config(),
        ):
            response = frontend_config(request)
        self.assertEqual(response.status_code, 405)

    @override_settings(DEBUG=True)
    def test_debug_flag_included(self):
        from core.views_api import frontend_config
        request = self.factory.get("/api/frontend-config/")
        with patch(
            "core.views_api.runtime_settings.get_runtime_config",
            return_value=self._mock_config(),
        ):
            response = frontend_config(request)
        data = json.loads(response.content)
        self.assertTrue(data["debug"])

    def test_response_includes_map_features(self):
        from core.views_api import frontend_config
        request = self.factory.get("/api/frontend-config/")
        with patch(
            "core.views_api.runtime_settings.get_runtime_config",
            return_value=self._mock_config(enable_map_clustering=False),
        ):
            response = frontend_config(request)
        data = json.loads(response.content)
        self.assertIn("enableMapClustering", data)
        self.assertIn("enableDrawingTools", data)
        self.assertIn("enableFullscreen", data)


class CoreRoutingTests(TestCase):
    """Ensure core.routing module is importable and exports the expected patterns."""

    def test_websocket_urlpatterns_exists(self):
        from core.routing import websocket_urlpatterns
        self.assertIsInstance(websocket_urlpatterns, list)
        self.assertGreater(len(websocket_urlpatterns), 0)

    def test_dashboard_ws_pattern_present(self):
        from core import routing
        routes = [str(p.pattern) for p in routing.websocket_urlpatterns]
        self.assertTrue(
            any("dashboard" in r for r in routes),
            msg=f"Expected 'dashboard' route in {routes}",
        )


class CoreUrlsZabbixProxyTests(TestCase):
    """Ensure core.urls_zabbix_proxy is importable (deprecated module guard)."""

    def test_module_importable(self):
        import core.urls_zabbix_proxy  # should not raise
