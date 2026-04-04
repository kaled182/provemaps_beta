"""Tests for maps_view.mapbox_proxy — proxy views."""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from django.test import RequestFactory, TestCase


def _make_requests_response(content=b"data", status=200, content_type="application/json"):
    resp = MagicMock()
    resp.content = content
    resp.status_code = status
    resp.headers = {"Content-Type": content_type}
    return resp


class MapboxProxyTokenTests(TestCase):
    def test_get_mapbox_token_with_config(self):
        from maps_view.mapbox_proxy import _get_mapbox_token
        mock_config = MagicMock()
        mock_config.mapbox_token = "pk.test-token"
        with patch(
            "maps_view.mapbox_proxy.FirstTimeSetup.objects.first",
            return_value=mock_config,
        ):
            token = _get_mapbox_token()
        self.assertEqual(token, "pk.test-token")

    def test_get_mapbox_token_no_config(self):
        from maps_view.mapbox_proxy import _get_mapbox_token
        with patch(
            "maps_view.mapbox_proxy.FirstTimeSetup.objects.first",
            return_value=None,
        ):
            token = _get_mapbox_token()
        self.assertIsNone(token)

    def test_get_mapbox_token_empty_token(self):
        from maps_view.mapbox_proxy import _get_mapbox_token
        mock_config = MagicMock()
        mock_config.mapbox_token = ""
        with patch(
            "maps_view.mapbox_proxy.FirstTimeSetup.objects.first",
            return_value=mock_config,
        ):
            token = _get_mapbox_token()
        self.assertIsNone(token)


class ProxyMapboxStyleTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()

    def _auth_request(self, path="/"):
        req = self.factory.get(path)
        req.user = MagicMock(is_authenticated=True, username="testuser")
        return req

    def test_no_token_returns_500(self):
        from maps_view.mapbox_proxy import proxy_mapbox_style
        req = self._auth_request()
        with patch(
            "maps_view.mapbox_proxy._get_mapbox_token", return_value=None
        ):
            resp = proxy_mapbox_style(req, style_id="mapbox/streets-v12")
        self.assertEqual(resp.status_code, 500)

    def test_proxies_style_successfully(self):
        from maps_view.mapbox_proxy import proxy_mapbox_style
        req = self._auth_request()
        mock_resp = _make_requests_response(b'{"style":"data"}')
        with patch(
            "maps_view.mapbox_proxy._get_mapbox_token", return_value="pk.token"
        ), patch("maps_view.mapbox_proxy.requests.get", return_value=mock_resp):
            resp = proxy_mapbox_style(req, style_id="mapbox/streets-v12")
        self.assertEqual(resp.status_code, 200)


class ProxyMapboxTilesTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()

    def _auth_request(self):
        req = self.factory.get("/")
        req.user = MagicMock(is_authenticated=True, username="testuser")
        return req

    def test_no_token_returns_500(self):
        from maps_view.mapbox_proxy import proxy_mapbox_tiles
        req = self._auth_request()
        with patch(
            "maps_view.mapbox_proxy._get_mapbox_token", return_value=None
        ):
            resp = proxy_mapbox_tiles(req, tileset="mapbox.streets", z=5, x=10, y=15)
        self.assertEqual(resp.status_code, 500)

    def test_proxies_tiles_successfully(self):
        from maps_view.mapbox_proxy import proxy_mapbox_tiles
        req = self._auth_request()
        mock_resp = _make_requests_response(
            b"\x1b\x4d", content_type="application/x-protobuf"
        )
        with patch(
            "maps_view.mapbox_proxy._get_mapbox_token", return_value="pk.token"
        ), patch("maps_view.mapbox_proxy.requests.get", return_value=mock_resp):
            resp = proxy_mapbox_tiles(
                req, tileset="mapbox.streets", z=5, x=10, y=15
            )
        self.assertEqual(resp.status_code, 200)


class ProxyMapboxSpritesTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()

    def _auth_request(self):
        req = self.factory.get("/")
        req.user = MagicMock(is_authenticated=True, username="testuser")
        return req

    def test_no_token_returns_500(self):
        from maps_view.mapbox_proxy import proxy_mapbox_sprites
        req = self._auth_request()
        with patch(
            "maps_view.mapbox_proxy._get_mapbox_token", return_value=None
        ):
            resp = proxy_mapbox_sprites(
                req, style_id="mapbox/streets-v12", sprite_file="sprite.json"
            )
        self.assertEqual(resp.status_code, 500)

    def test_png_sprite_content_type(self):
        from maps_view.mapbox_proxy import proxy_mapbox_sprites
        req = self._auth_request()
        mock_resp = _make_requests_response(b"PNG", content_type="image/png")
        with patch(
            "maps_view.mapbox_proxy._get_mapbox_token", return_value="pk.token"
        ), patch("maps_view.mapbox_proxy.requests.get", return_value=mock_resp):
            resp = proxy_mapbox_sprites(
                req, style_id="mapbox/streets-v12", sprite_file="sprite.png"
            )
        self.assertEqual(resp.status_code, 200)

    def test_json_sprite(self):
        from maps_view.mapbox_proxy import proxy_mapbox_sprites
        req = self._auth_request()
        mock_resp = _make_requests_response(b"{}", content_type="application/json")
        with patch(
            "maps_view.mapbox_proxy._get_mapbox_token", return_value="pk.token"
        ), patch("maps_view.mapbox_proxy.requests.get", return_value=mock_resp):
            resp = proxy_mapbox_sprites(
                req, style_id="mapbox/streets-v12", sprite_file="sprite.json"
            )
        self.assertEqual(resp.status_code, 200)

    def test_webp_sprite(self):
        from maps_view.mapbox_proxy import proxy_mapbox_sprites
        req = self._auth_request()
        mock_resp = _make_requests_response(b"WEBP", content_type="image/webp")
        with patch(
            "maps_view.mapbox_proxy._get_mapbox_token", return_value="pk.token"
        ), patch("maps_view.mapbox_proxy.requests.get", return_value=mock_resp):
            resp = proxy_mapbox_sprites(
                req, style_id="mapbox/streets-v12", sprite_file="sprite.webp"
            )
        self.assertEqual(resp.status_code, 200)


class ProxyMapboxGlyphsTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()

    def _auth_request(self):
        req = self.factory.get("/")
        req.user = MagicMock(is_authenticated=True, username="testuser")
        return req

    def test_no_token_returns_500(self):
        from maps_view.mapbox_proxy import proxy_mapbox_glyphs
        req = self._auth_request()
        with patch(
            "maps_view.mapbox_proxy._get_mapbox_token", return_value=None
        ):
            resp = proxy_mapbox_glyphs(
                req, font_stack="Open Sans Regular", glyph_range="0-255"
            )
        self.assertEqual(resp.status_code, 500)

    def test_proxies_glyphs_successfully(self):
        from maps_view.mapbox_proxy import proxy_mapbox_glyphs
        req = self._auth_request()
        mock_resp = _make_requests_response(
            b"PBF", content_type="application/x-protobuf"
        )
        with patch(
            "maps_view.mapbox_proxy._get_mapbox_token", return_value="pk.token"
        ), patch("maps_view.mapbox_proxy.requests.get", return_value=mock_resp):
            resp = proxy_mapbox_glyphs(
                req, font_stack="Open Sans Regular", glyph_range="0-255"
            )
        self.assertEqual(resp.status_code, 200)


class LogRequestTests(TestCase):
    def test_log_request_does_not_raise(self):
        from maps_view.mapbox_proxy import _log_request
        factory = RequestFactory()
        req = factory.get("/proxy/style/")
        req.user = MagicMock(is_authenticated=True, username="u1")
        _log_request(req, "style")
