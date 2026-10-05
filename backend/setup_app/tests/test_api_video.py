"""Views de vídeo (EV-0017d): acesso, códigos HTTP, proxy HLS e tradução das exceções."""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import requests
from django.contrib.auth.models import User
from django.test import TestCase

from setup_app.models import MessagingGateway, VideoMosaic
from setup_app.usecases import video as uc

API = "setup_app.api.video"


class VideoApiTests(TestCase):
    def setUp(self):
        self.staff = User.objects.create_user(
            username="v_staff", password="pass", email="v@t.com", is_staff=True, is_active=True
        )
        self.client.force_login(self.staff)
        self.gw = MessagingGateway.objects.create(
            name="Cam", gateway_type="video", config={"stream_url": "rtsp://x"}
        )
        patch(f"{uc.__name__}.video_gateway_service.build_playback_url", return_value="").start()
        self.addCleanup(patch.stopall)

    def _post(self, url, body=None):
        return self.client.post(url, json.dumps(body or {}), content_type="application/json")

    # ── HLS ──────────────────────────────────────────────────────────────────

    def _upstream(self, status=200, headers=None, content=b""):
        up = MagicMock()
        up.status_code = status
        up.headers = headers or {}
        up.content = content
        up.iter_content.return_value = iter([b"a", b"", b"b"])
        return up

    def test_hls_proxy_streams_and_passes_headers(self):
        up = self._upstream(headers={"ETag": "e1", "Content-Type": "video/mp2t"})
        with (
            patch(f"{API}.requests.get", return_value=up) as get,
            patch(f"{uc.__name__}.video_gateway_service.get_stream_key", return_value="k"),
            patch(
                f"{uc.__name__}.video_gateway_service.build_internal_hls_url",
                return_value="http://hls/k/seg.ts",
            ),
        ):
            resp = self.client.get(f"/setup_app/video/hls/gateways/{self.gw.id}/seg.ts?x=1")
            body = b"".join(resp.streaming_content)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(body, b"ab")
        self.assertEqual(resp["Content-Type"], "video/mp2t")
        self.assertEqual(resp["ETag"], "e1")
        self.assertEqual(resp["Cache-Control"], "no-cache, private")
        self.assertEqual(get.call_args.kwargs["params"], {"x": "1", "mode": "legacy"})
        up.close.assert_called_once()

    def test_hls_proxy_default_manifest_content_type(self):
        up = self._upstream()
        with (
            patch(f"{API}.requests.get", return_value=up),
            patch(f"{uc.__name__}.video_gateway_service.get_stream_key", return_value="k"),
            patch(f"{uc.__name__}.video_gateway_service.build_internal_hls_url", return_value="u"),
        ):
            resp = self.client.get(f"/setup_app/video/hls/gateways/{self.gw.id}/")
        self.assertEqual(resp["Content-Type"], "application/vnd.apple.mpegurl")

    def test_hls_proxy_errors(self):
        self.assertEqual(self.client.get("/setup_app/video/hls/gateways/99999/").status_code, 404)
        resp = self.client.get(f"/setup_app/video/hls/gateways/{self.gw.id}/../x")
        self.assertIn(resp.status_code, (400, 404))
        with (
            patch(f"{API}.requests.get", side_effect=requests.ConnectionError("down")),
            patch(f"{uc.__name__}.video_gateway_service.get_stream_key", return_value="k"),
            patch(f"{uc.__name__}.video_gateway_service.build_internal_hls_url", return_value="u"),
        ):
            resp = self.client.get(f"/setup_app/video/hls/gateways/{self.gw.id}/")
        self.assertEqual(resp.status_code, 502)
        up = self._upstream(
            status=404, headers={"Content-Type": "text/plain"}, content=b"nf" * 5000
        )
        with (
            patch(f"{API}.requests.get", return_value=up),
            patch(f"{uc.__name__}.video_gateway_service.get_stream_key", return_value="k"),
            patch(f"{uc.__name__}.video_gateway_service.build_internal_hls_url", return_value="u"),
        ):
            resp = self.client.get(f"/setup_app/video/hls/gateways/{self.gw.id}/")
        self.assertEqual(resp.status_code, 404)
        self.assertEqual(len(resp.content), 4096)

    # ── preview ──────────────────────────────────────────────────────────────

    def test_preview_start_ok_adds_proxy_url(self):
        with patch(
            f"{API}.usecase.start_preview", return_value={"preview_url": "p", "playback_url": "q"}
        ):
            resp = self._post(f"/setup_app/api/gateways/{self.gw.id}/video/preview/start/")
        self.assertEqual(resp.status_code, 200)
        data = json.loads(resp.content)
        self.assertEqual(data["preview_url"], "p")
        self.assertTrue(
            data["playback_proxy_url"].endswith(f"/video/hls/gateways/{self.gw.id}/index.m3u8")
        )

    def test_preview_start_errors(self):
        for exc, status in (
            (uc.VideoError("cfg"), 400),
            (uc.PreviewTimeout("t"), 504),
            (uc.PreviewServiceError("s"), 502),
            (uc.PreviewFailed("f"), 500),
        ):
            with patch(f"{API}.usecase.start_preview", side_effect=exc):
                resp = self._post(f"/setup_app/api/gateways/{self.gw.id}/video/preview/start/")
            self.assertEqual(resp.status_code, status, exc)
        resp = self._post("/setup_app/api/gateways/99999/video/preview/start/")
        self.assertEqual(resp.status_code, 404)

    def test_preview_stop(self):
        with patch(f"{API}.usecase.stop_preview") as stop:
            resp = self._post(f"/setup_app/api/gateways/{self.gw.id}/video/preview/stop/")
        self.assertEqual(json.loads(resp.content), {"success": True})
        stop.assert_called_once_with(self.gw)

    # ── câmeras e mosaicos ───────────────────────────────────────────────────

    def test_cameras_list(self):
        resp = self.client.get("/api/v1/cameras/")
        self.assertEqual(resp.status_code, 200)
        data = json.loads(resp.content)
        self.assertEqual(data["count"], 1)
        self.assertEqual(data["results"][0]["name"], "Cam")
        with patch(f"{API}.usecase.list_cameras_for", side_effect=RuntimeError("x")):
            self.assertEqual(self.client.get("/api/v1/cameras/").status_code, 500)

    def test_mosaics_list_create(self):
        VideoMosaic.objects.create(name="M1")
        resp = self.client.get("/setup_app/video/api/mosaics/")
        self.assertEqual([m["name"] for m in json.loads(resp.content)["mosaics"]], ["M1"])

        resp = self._post("/setup_app/video/api/mosaics/", {"name": "M2", "layout": "3x3"})
        self.assertEqual(resp.status_code, 200)
        data = json.loads(resp.content)
        self.assertEqual(data["message"], "Mosaico criado com sucesso")
        self.assertEqual(data["mosaic"]["layout"], "3x3")

        resp = self._post("/setup_app/video/api/mosaics/", {"name": ""})
        self.assertEqual(resp.status_code, 400)
        resp = self.client.post(
            "/setup_app/video/api/mosaics/", "{bad", content_type="application/json"
        )
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(json.loads(resp.content)["message"], "Invalid JSON data")

    def test_mosaic_detail(self):
        m = VideoMosaic.objects.create(name="M")
        url = f"/setup_app/video/api/mosaics/{m.id}/"
        self.assertEqual(json.loads(self.client.get(url).content)["mosaic"]["name"], "M")
        resp = self.client.patch(url, json.dumps({"name": "N"}), content_type="application/json")
        self.assertEqual(json.loads(resp.content)["mosaic"]["name"], "N")
        resp = self.client.patch(url, json.dumps({"name": ""}), content_type="application/json")
        self.assertEqual(resp.status_code, 400)
        resp = self.client.delete(url)
        self.assertEqual(json.loads(resp.content)["message"], "Mosaico 'N' removido com sucesso")
        self.assertEqual(self.client.get(url).status_code, 404)
        with patch(f"{API}.usecase.get_mosaic_for", side_effect=uc.VideoForbidden("no")):
            self.assertEqual(self.client.get(url).status_code, 403)

    # ── definições e teste de stream (login basta) ───────────────────────────

    def test_camera_settings_get_post(self):
        regular = User.objects.create_user(username="v_user", password="pass", email="u@t.com")
        self.client.force_login(regular)
        with patch(f"{uc.__name__}.env_manager.read_values", return_value={}):
            resp = self.client.get("/setup_app/api/camera-settings/")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(json.loads(resp.content)["settings"]["default_fps"], 30)
        with patch(f"{uc.__name__}.env_manager.write_values") as write:
            resp = self._post("/setup_app/api/camera-settings/", {"default_fps": 15})
        self.assertEqual(json.loads(resp.content)["message"], "Configurações de câmeras salvas.")
        write.assert_called_once_with({"CAMERA_DEFAULT_FPS": "15"})
        resp = self.client.post(
            "/setup_app/api/camera-settings/", "{bad", content_type="application/json"
        )
        self.assertEqual(resp.status_code, 400)
        self.assertIn("Invalid JSON", json.loads(resp.content)["message"])

    def test_test_stream(self):
        resp = self._post("/setup_app/api/test-stream/", {"stream_url": ""})
        self.assertEqual(resp.status_code, 400)
        with patch(f"{uc.__name__}.socket.create_connection", side_effect=OSError("refused")):
            resp = self._post("/setup_app/api/test-stream/", {"stream_url": "rtsp://h:1/x"})
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(
            json.loads(resp.content), {"success": False, "message": "Falha na conexão: refused"}
        )
        with patch(f"{uc.__name__}.socket.create_connection"):
            resp = self._post(
                "/setup_app/api/test-stream/", {"stream_url": "rtsp://h/x", "timeout": "2"}
            )
        self.assertTrue(json.loads(resp.content)["success"])
