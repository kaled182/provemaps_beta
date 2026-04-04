"""Tests for setup_app.services.video_gateway — pure helper functions."""
from __future__ import annotations

import os
from unittest.mock import MagicMock, patch

from django.test import TestCase, override_settings


class GetTransmuxerUrlTests(TestCase):
    @override_settings(VIDEO_TRANSMUXER_URL="http://my-transmuxer:9000")
    def test_reads_from_settings(self):
        from setup_app.services.video_gateway import _get_transmuxer_url
        url = _get_transmuxer_url()
        self.assertEqual(url, "http://my-transmuxer:9000")

    def test_reads_from_env(self):
        from setup_app.services.video_gateway import _get_transmuxer_url
        with override_settings(VIDEO_TRANSMUXER_URL=None), \
             patch.dict(os.environ, {"VIDEO_TRANSMUXER_URL": "http://env-transmuxer:9001"}):
            url = _get_transmuxer_url()
        self.assertEqual(url, "http://env-transmuxer:9001")

    def test_default_value(self):
        from setup_app.services.video_gateway import _get_transmuxer_url
        with override_settings(VIDEO_TRANSMUXER_URL=None), \
             patch.dict(os.environ, {}):
            os.environ.pop("VIDEO_TRANSMUXER_URL", None)  # safe: inside patch.dict
            url = _get_transmuxer_url()
        self.assertIn("video-transmuxer", url)

    def test_strips_trailing_slash(self):
        from setup_app.services.video_gateway import _get_transmuxer_url
        with override_settings(VIDEO_TRANSMUXER_URL="http://host:9000/"):
            url = _get_transmuxer_url()
        self.assertFalse(url.endswith("/"))


class GetHlsProbeBaseUrlTests(TestCase):
    @override_settings(VIDEO_HLS_BASE_URL="http://hls.local:8080/hls")
    def test_reads_from_settings(self):
        from setup_app.services.video_gateway import _get_hls_probe_base_url
        url = _get_hls_probe_base_url()
        self.assertEqual(url, "http://hls.local:8080/hls")

    def test_strips_trailing_slash(self):
        from setup_app.services.video_gateway import _get_hls_probe_base_url
        with override_settings(VIDEO_HLS_BASE_URL="http://hls:8080/hls/"):
            url = _get_hls_probe_base_url()
        self.assertFalse(url.endswith("/"))


class GetHlsPublicBaseUrlTests(TestCase):
    def test_uses_config_override(self):
        from setup_app.services.video_gateway import _get_hls_public_base_url
        config = {"hls_public_base_url": "http://public-hls.example"}
        url = _get_hls_public_base_url(config)
        self.assertEqual(url, "http://public-hls.example")

    @override_settings(VIDEO_HLS_PUBLIC_BASE_URL="http://settings-public")
    def test_reads_from_settings(self):
        from setup_app.services.video_gateway import _get_hls_public_base_url
        url = _get_hls_public_base_url()
        self.assertEqual(url, "http://settings-public")

    def test_falls_back_to_probe_url(self):
        from setup_app.services.video_gateway import _get_hls_public_base_url
        with override_settings(VIDEO_HLS_PUBLIC_BASE_URL=None, VIDEO_HLS_BASE_URL="http://probe:8080/hls"), \
             patch.dict(os.environ, {}):
            os.environ.pop("VIDEO_HLS_PUBLIC_BASE_URL", None)
            url = _get_hls_public_base_url()
        self.assertIn("probe", url)

    def test_empty_config_override_uses_settings(self):
        from setup_app.services.video_gateway import _get_hls_public_base_url
        config = {"hls_public_base_url": ""}
        with override_settings(VIDEO_HLS_PUBLIC_BASE_URL="http://settings"):
            url = _get_hls_public_base_url(config)
        self.assertEqual(url, "http://settings")


class GetWebrtcManifestTimeoutTests(TestCase):
    def test_reads_from_config(self):
        from setup_app.services.video_gateway import _get_webrtc_manifest_timeout
        config = {"webrtc_manifest_grace_seconds": "45"}
        timeout = _get_webrtc_manifest_timeout(config)
        self.assertEqual(timeout, 45.0)

    def test_default_fallback(self):
        from setup_app.services.video_gateway import _get_webrtc_manifest_timeout
        with override_settings(VIDEO_WEBRTC_HLS_GRACE_SECONDS=None), \
             patch.dict(os.environ, {}):
            os.environ.pop("VIDEO_WEBRTC_HLS_GRACE_SECONDS", None)
            timeout = _get_webrtc_manifest_timeout()
        self.assertEqual(timeout, 20.0)

    def test_clamps_minimum_to_3(self):
        from setup_app.services.video_gateway import _get_webrtc_manifest_timeout
        config = {"webrtc_manifest_grace_seconds": "1"}
        timeout = _get_webrtc_manifest_timeout(config)
        self.assertEqual(timeout, 3.0)

    def test_clamps_maximum_to_120(self):
        from setup_app.services.video_gateway import _get_webrtc_manifest_timeout
        config = {"webrtc_manifest_grace_seconds": "999"}
        timeout = _get_webrtc_manifest_timeout(config)
        self.assertEqual(timeout, 120.0)

    def test_invalid_config_value_uses_fallback(self):
        from setup_app.services.video_gateway import _get_webrtc_manifest_timeout
        config = {"webrtc_manifest_grace_seconds": "not-a-number"}
        with override_settings(VIDEO_WEBRTC_HLS_GRACE_SECONDS=None), \
             patch.dict(os.environ, {}):
            os.environ.pop("VIDEO_WEBRTC_HLS_GRACE_SECONDS", None)
            timeout = _get_webrtc_manifest_timeout(config)
        self.assertEqual(timeout, 20.0)

    def test_reads_grace_seconds_from_env(self):
        from setup_app.services.video_gateway import _get_webrtc_manifest_timeout
        with override_settings(VIDEO_WEBRTC_HLS_GRACE_SECONDS=None), \
             patch.dict(os.environ, {"VIDEO_WEBRTC_HLS_GRACE_SECONDS": "30"}):
            timeout = _get_webrtc_manifest_timeout()
        self.assertEqual(timeout, 30.0)


class GetStreamKeyTests(TestCase):
    def test_uses_restream_key_from_config(self):
        from setup_app.services.video_gateway import _get_stream_key
        gw = MagicMock()
        gw.config = {"restream_key": "my-stream"}
        gw.id = 99
        key = _get_stream_key(gw)
        self.assertEqual(key, "my-stream")

    def test_falls_back_to_gateway_id(self):
        from setup_app.services.video_gateway import _get_stream_key
        gw = MagicMock()
        gw.config = {}
        gw.id = 42
        key = _get_stream_key(gw)
        self.assertEqual(key, "gateway_42")

    def test_public_get_stream_key_delegates(self):
        from setup_app.services.video_gateway import get_stream_key
        gw = MagicMock()
        gw.config = {"restream_key": "pub-key"}
        gw.id = 1
        self.assertEqual(get_stream_key(gw), "pub-key")

    def test_none_config_falls_back_to_id(self):
        from setup_app.services.video_gateway import _get_stream_key
        gw = MagicMock()
        gw.config = None
        gw.id = 7
        key = _get_stream_key(gw)
        self.assertEqual(key, "gateway_7")


class BuildInternalHlsUrlTests(TestCase):
    @override_settings(VIDEO_HLS_BASE_URL="http://hls:8080/hls")
    def test_builds_correct_url(self):
        from setup_app.services.video_gateway import build_internal_hls_url
        url = build_internal_hls_url("mystream", "index.m3u8")
        self.assertEqual(url, "http://hls:8080/hls/live/mystream/index.m3u8")

    @override_settings(VIDEO_HLS_BASE_URL="http://hls:8080/hls")
    def test_strips_leading_slash_from_resource(self):
        from setup_app.services.video_gateway import build_internal_hls_url
        url = build_internal_hls_url("key", "/index.m3u8")
        # No double-slash after the authority
        self.assertFalse("//" in url.split("//", 1)[1])


class BuildPlaybackUrlTests(TestCase):
    def test_returns_stored_preview_playback_url(self):
        from setup_app.services.video_gateway import build_playback_url
        gw = MagicMock()
        gw.config = {"preview_playback_url": "http://stored/index.m3u8"}
        url = build_playback_url(gw)
        self.assertEqual(url, "http://stored/index.m3u8")

    def test_returns_preview_url_when_hls(self):
        from setup_app.services.video_gateway import build_playback_url
        gw = MagicMock()
        gw.config = {"preview_url": "http://live/stream.m3u8"}
        url = build_playback_url(gw)
        self.assertEqual(url, "http://live/stream.m3u8")

    def test_returns_stream_url_when_http(self):
        from setup_app.services.video_gateway import build_playback_url
        gw = MagicMock()
        gw.config = {"stream_url": "http://direct/stream"}
        url = build_playback_url(gw)
        self.assertEqual(url, "http://direct/stream")

    @override_settings(VIDEO_HLS_PUBLIC_BASE_URL="http://public-hls")
    def test_builds_hls_url_from_stream_key(self):
        from setup_app.services.video_gateway import build_playback_url
        gw = MagicMock()
        gw.config = {"restream_key": "cam1"}
        gw.id = 1
        url = build_playback_url(gw)
        self.assertIn("cam1", url)
        self.assertIn("index.m3u8", url)

    def test_returns_empty_when_no_config(self):
        from setup_app.services.video_gateway import build_playback_url
        gw = MagicMock()
        gw.config = {}
        gw.id = 5
        with override_settings(VIDEO_HLS_PUBLIC_BASE_URL=None, VIDEO_HLS_BASE_URL=None), \
             patch.dict(os.environ, {}):
            os.environ.pop("VIDEO_HLS_PUBLIC_BASE_URL", None)
            os.environ.pop("VIDEO_HLS_BASE_URL", None)
            url = build_playback_url(gw)
        self.assertEqual(url, "")


class GetWebrtcPublicBaseUrlTests(TestCase):
    def test_uses_config_override(self):
        from setup_app.services.video_gateway import _get_webrtc_public_base_url
        config = {"webrtc_public_base_url": "http://webrtc.example"}
        url = _get_webrtc_public_base_url(config)
        self.assertEqual(url, "http://webrtc.example")

    @override_settings(VIDEO_WEBRTC_PUBLIC_BASE_URL="http://settings-webrtc")
    def test_reads_from_settings(self):
        from setup_app.services.video_gateway import _get_webrtc_public_base_url
        url = _get_webrtc_public_base_url()
        self.assertEqual(url, "http://settings-webrtc")

    def test_returns_none_when_no_config(self):
        from setup_app.services.video_gateway import _get_webrtc_public_base_url
        with override_settings(VIDEO_WEBRTC_PUBLIC_BASE_URL=None), \
             patch.dict(os.environ, {}):
            os.environ.pop("VIDEO_WEBRTC_PUBLIC_BASE_URL", None)
            url = _get_webrtc_public_base_url()
        self.assertIsNone(url)

    def test_strips_trailing_slash(self):
        from setup_app.services.video_gateway import _get_webrtc_public_base_url
        config = {"webrtc_public_base_url": "http://webrtc.example/"}
        url = _get_webrtc_public_base_url(config)
        self.assertFalse(url.endswith("/"))


class StopStreamForGatewayTests(TestCase):
    def test_calls_delete_and_persists(self):
        from setup_app.services.video_gateway import stop_stream_for_gateway
        gw = MagicMock()
        gw.config = {"restream_key": "stream1"}
        gw.id = 1
        with patch("setup_app.services.video_gateway.requests.delete") as mock_del, \
             patch("setup_app.services.video_gateway._persist_config") as mock_persist:
            mock_del.return_value = MagicMock(status_code=200)
            stop_stream_for_gateway(gw)
        mock_del.assert_called_once()
        mock_persist.assert_called_once()

    def test_handles_request_exception(self):
        import requests as _requests
        from setup_app.services.video_gateway import stop_stream_for_gateway
        gw = MagicMock()
        gw.config = {"restream_key": "stream1"}
        gw.id = 1
        with patch("setup_app.services.video_gateway.requests.delete",
                   side_effect=_requests.RequestException("timeout")), \
             patch("setup_app.services.video_gateway._persist_config") as mock_persist:
            stop_stream_for_gateway(gw)
        mock_persist.assert_called_once()

    def test_clear_preview_removes_urls(self):
        from setup_app.services.video_gateway import stop_stream_for_gateway
        gw = MagicMock()
        gw.config = {"restream_key": "stream1"}
        gw.id = 1
        with patch("setup_app.services.video_gateway.requests.delete") as mock_del, \
             patch("setup_app.services.video_gateway._persist_config") as mock_persist:
            mock_del.return_value = MagicMock(status_code=404)
            stop_stream_for_gateway(gw, clear_preview=True)
        updates = mock_persist.call_args[0][1]
        self.assertIn("preview_url", updates)
        self.assertIn("preview_playback_url", updates)

    def test_warn_on_non_200_non_404(self):
        from setup_app.services.video_gateway import stop_stream_for_gateway
        gw = MagicMock()
        gw.config = {}
        gw.id = 1
        with patch("setup_app.services.video_gateway.requests.delete") as mock_del, \
             patch("setup_app.services.video_gateway._persist_config"):
            mock_del.return_value = MagicMock(status_code=500, text="err")
            stop_stream_for_gateway(gw)  # should not raise


class SyncGatewayStreamTests(TestCase):
    def test_non_video_gateway_returns_early(self):
        from setup_app.services.video_gateway import sync_gateway_stream
        gw = MagicMock()
        gw.gateway_type = "sms"
        with patch("setup_app.services.video_gateway.stop_stream_for_gateway") as mock_stop, \
             patch("setup_app.services.video_gateway.ensure_stream_for_gateway") as mock_ensure:
            sync_gateway_stream(gw)
        mock_stop.assert_not_called()
        mock_ensure.assert_not_called()

    def test_disabled_gateway_stops_stream(self):
        from setup_app.services.video_gateway import sync_gateway_stream
        gw = MagicMock()
        gw.gateway_type = "video"
        gw.enabled = False
        with patch("setup_app.services.video_gateway.stop_stream_for_gateway") as mock_stop:
            sync_gateway_stream(gw)
        mock_stop.assert_called_once_with(gw)

    def test_enabled_gateway_ensures_stream(self):
        from setup_app.services.video_gateway import sync_gateway_stream
        gw = MagicMock()
        gw.gateway_type = "video"
        gw.enabled = True
        with patch("setup_app.services.video_gateway.ensure_stream_for_gateway") as mock_ensure:
            sync_gateway_stream(gw)
        mock_ensure.assert_called_once_with(gw)
