"""Usecases de vídeo (EV-0017d): HLS, pré-visualização, câmeras, mosaicos, definições, teste de stream."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from django.contrib.auth.models import User
from django.test import TestCase, override_settings

from core.models import Department
from inventory.models import Site
from setup_app.models import MessagingGateway, VideoMosaic
from setup_app.usecases import video as uc

UC = "setup_app.usecases.video"


class HlsAndPreviewTests(TestCase):
    def setUp(self):
        self.gw = MessagingGateway.objects.create(
            name="Cam", gateway_type="video", config={"stream_url": "rtsp://x"}
        )

    def test_get_video_gateway(self):
        self.assertEqual(uc.get_video_gateway(self.gw.id), self.gw)
        MessagingGateway.objects.create(name="S", gateway_type="sms")
        with self.assertRaises(uc.VideoNotFound) as ctx:
            uc.get_video_gateway(99999)
        self.assertEqual(ctx.exception.status, 404)
        self.assertEqual(str(ctx.exception), "Gateway de vídeo não encontrado.")

    def test_require_video_access(self):
        user = MagicMock(is_superuser=False)
        user.profile = None
        self.gw.departments.add(Department.objects.create(name="D"))
        with self.assertRaises(uc.VideoForbidden) as ctx:
            uc.require_video_access(user, self.gw)
        self.assertEqual(ctx.exception.status, 403)
        uc.require_video_access(MagicMock(is_superuser=True), self.gw)

    def test_sanitize_hls_resource(self):
        self.assertEqual(uc.sanitize_hls_resource(None), "index.m3u8")
        self.assertEqual(uc.sanitize_hls_resource(""), "index.m3u8")
        self.assertEqual(uc.sanitize_hls_resource("seg/"), "seg/index.m3u8")
        self.assertEqual(uc.sanitize_hls_resource("/a/b.ts"), "a/b.ts")
        with self.assertRaises(uc.VideoError):
            uc.sanitize_hls_resource("../etc/passwd")

    def test_hls_content_type(self):
        self.assertEqual(uc.hls_content_type("x.m3u8", None), "application/vnd.apple.mpegurl")
        self.assertEqual(uc.hls_content_type("x.ts", None), "application/octet-stream")
        self.assertEqual(uc.hls_content_type("x.ts", "video/mp2t"), "video/mp2t")

    def test_hls_target_url_uses_service(self):
        with (
            patch(f"{UC}.video_gateway_service.get_stream_key", return_value="k"),
            patch(
                f"{UC}.video_gateway_service.build_internal_hls_url", return_value="http://h"
            ) as build,
        ):
            self.assertEqual(uc.hls_target_url(self.gw, "index.m3u8"), "http://h")
        build.assert_called_once_with("k", "index.m3u8")

    def test_start_preview_requires_stream_url(self):
        self.gw.config = {}
        with self.assertRaises(uc.VideoError) as ctx:
            uc.start_preview(self.gw)
        self.assertIn("Configure a URL do stream", str(ctx.exception))

    def test_start_preview_ok(self):
        def _ensure(gateway, **kwargs):
            gateway.config = {**gateway.config, "preview_url": "http://p"}
            gateway.save()

        with (
            patch(f"{UC}.video_gateway_service.ensure_stream_for_gateway", side_effect=_ensure),
            patch(f"{UC}.video_gateway_service.build_playback_url", return_value="http://play"),
        ):
            result = uc.start_preview(self.gw)
        self.assertEqual(result, {"preview_url": "http://p", "playback_url": "http://play"})

    def test_start_preview_maps_service_errors(self):
        svc = uc.video_gateway_service
        for side_effect, exc_type, status in (
            (svc.PreviewStartTimeout("t"), uc.PreviewTimeout, 504),
            (svc.VideoGatewayError("e"), uc.PreviewServiceError, 502),
        ):
            with patch(
                f"{UC}.video_gateway_service.ensure_stream_for_gateway", side_effect=side_effect
            ):
                with self.assertRaises(exc_type) as ctx:
                    uc.start_preview(self.gw)
            self.assertEqual(ctx.exception.status, status)

    def test_stop_preview(self):
        with patch(f"{UC}.video_gateway_service.stop_stream_for_gateway") as stop:
            uc.stop_preview(self.gw)
        stop.assert_called_once_with(self.gw)
        with patch(f"{UC}.video_gateway_service.stop_stream_for_gateway", side_effect=RuntimeError):
            with self.assertRaises(uc.PreviewFailed) as ctx:
                uc.stop_preview(self.gw)
        self.assertEqual(ctx.exception.status, 500)


class CamerasAndMosaicsTests(TestCase):
    def setUp(self):
        patch(f"{UC}.video_gateway_service.build_playback_url", return_value="http://play").start()
        self.addCleanup(patch.stopall)
        self.superuser = User.objects.create_superuser("vsu", "vsu@t.com", "p")
        self.user = User.objects.create_user("vu", "vu@t.com", "p", is_staff=True)
        self.dept_a = Department.objects.create(name="VA")
        self.dept_b = Department.objects.create(name="VB")
        self.user.profile.departments.add(self.dept_a)
        self.site = Site.objects.create(display_name="Hub")
        self.pub = MessagingGateway.objects.create(
            name="Pub", gateway_type="video", site_name="Hub", config={"restream_key": "rk"}
        )
        self.cam_a = MessagingGateway.objects.create(name="A", gateway_type="video")
        self.cam_a.departments.add(self.dept_a)
        self.cam_b = MessagingGateway.objects.create(name="B", gateway_type="video")
        self.cam_b.departments.add(self.dept_b)
        self.off = MessagingGateway.objects.create(name="Off", gateway_type="video", enabled=False)

    @override_settings(VIDEO_WEBRTC_PUBLIC_BASE_URL="http://media/")
    def test_list_cameras_rbac_site_filter_and_whep(self):
        names = [c["name"] for c in uc.list_cameras_for(self.superuser)]
        self.assertEqual(names, ["A", "B", "Pub"])  # desativadas ficam fora
        names = [c["name"] for c in uc.list_cameras_for(self.user)]
        self.assertEqual(names, ["A", "Pub"])
        cams = uc.list_cameras_for(self.user, str(self.site.id))
        self.assertEqual([c["name"] for c in cams], ["Pub"])
        self.assertEqual(cams[0]["whep_url"], "http://media/whep/rk")
        self.assertEqual(cams[0]["playback_url"], "http://play")
        self.assertEqual(len(uc.list_cameras_for(self.user, "not-an-id")), 2)  # filtro ignorado

    @override_settings(VIDEO_WEBRTC_PUBLIC_BASE_URL=None)
    def test_whep_url_absent_without_base(self):
        with patch.dict("os.environ", {}, clear=False):
            import os

            os.environ.pop("VIDEO_WEBRTC_PUBLIC_BASE_URL", None)
            cams = {c["name"]: c for c in uc.list_cameras_for(self.superuser)}
        self.assertIsNone(cams["A"]["whep_url"])

    def test_mosaics_crud_and_rbac(self):
        m_pub = VideoMosaic.objects.create(name="Pub", layout="2x2")
        m_a = VideoMosaic.objects.create(name="A", layout="3x3", site=self.site)
        m_a.departments.add(self.dept_a)
        m_b = VideoMosaic.objects.create(name="B")
        m_b.departments.add(self.dept_b)

        self.assertEqual(
            [m["name"] for m in uc.list_mosaics_for(self.superuser)], ["A", "B", "Pub"]
        )
        self.assertEqual([m["name"] for m in uc.list_mosaics_for(self.user)], ["A", "Pub"])
        self.assertEqual(
            [m["name"] for m in uc.list_mosaics_for(self.user, str(self.site.id))], ["A"]
        )
        self.assertEqual(len(uc.list_mosaics_for(self.user, "x")), 2)

        self.assertEqual(uc.get_mosaic_for(self.user, m_a.id), m_a)
        self.assertEqual(uc.get_mosaic_for(self.user, m_pub.id), m_pub)
        with self.assertRaises(uc.VideoForbidden):
            uc.get_mosaic_for(self.user, m_b.id)
        with self.assertRaises(uc.VideoNotFound):
            uc.get_mosaic_for(self.user, 99999)

        with self.assertRaises(uc.VideoError):
            uc.create_mosaic(self.user, {"name": " "})
        with self.assertRaises(uc.VideoForbidden):
            uc.create_mosaic(self.user, {"name": "X", "department_ids": [self.dept_b.id]})
        created = uc.create_mosaic(
            self.user,
            {
                "name": "Novo",
                "cameras": [self.cam_a.id],
                "site_id": "nope",
                "department_ids": [self.dept_a.id],
            },
        )
        self.assertEqual(created["layout"], "2x2")
        self.assertIsNone(created["site_id"])
        self.assertEqual(created["departments"], [{"id": self.dept_a.id, "name": "VA"}])
        self.assertEqual(created["cameras"], [self.cam_a.id])

        mosaic = VideoMosaic.objects.get(id=created["id"])
        with self.assertRaises(uc.VideoError):
            uc.update_mosaic(self.user, mosaic, {"name": ""})
        with self.assertRaises(uc.VideoForbidden):
            uc.update_mosaic(self.user, mosaic, {"department_ids": [self.dept_b.id]})
        updated = uc.update_mosaic(
            self.user,
            mosaic,
            {"name": "Novo2", "layout": "4x4", "site_id": self.site.id, "department_ids": []},
        )
        self.assertEqual(updated["name"], "Novo2")
        self.assertEqual(updated["layout"], "4x4")
        self.assertEqual(updated["site_id"], self.site.id)
        self.assertEqual(updated["departments"], [])

        self.assertEqual(uc.delete_mosaic(mosaic), "Novo2")
        self.assertFalse(VideoMosaic.objects.filter(id=created["id"]).exists())


class CameraSettingsAndStreamTests(TestCase):
    def test_get_camera_settings_types(self):
        raw = {
            "CAMERA_DEFAULT_FPS": "60",
            "CAMERA_ENABLE_HARDWARE_ACCELERATION": "no",
            "CAMERA_MAX_CONCURRENT_STREAMS": "abc",
            "CAMERA_DEFAULT_CODEC": "h265",
            "CAMERA_RECONNECT_ATTEMPTS": "",
        }
        with patch(f"{UC}.env_manager.read_values", return_value=raw):
            result = uc.get_camera_settings()
        self.assertEqual(result["default_fps"], 60)
        self.assertIs(result["enable_hardware_acceleration"], False)
        self.assertEqual(result["max_concurrent_streams"], 10)  # inválido mantém o default
        self.assertEqual(result["default_codec"], "h265")
        self.assertEqual(result["reconnect_attempts"], 3)
        self.assertEqual(result["default_stream_type"], "rtmp")

    def test_save_camera_settings_writes_only_present_keys(self):
        with patch(f"{UC}.env_manager.write_values") as write:
            written = uc.save_camera_settings(
                {"default_fps": 25, "enable_hardware_acceleration": 0, "unknown": 1}
            )
        self.assertEqual(
            written, {"CAMERA_DEFAULT_FPS": "25", "CAMERA_ENABLE_HARDWARE_ACCELERATION": "false"}
        )
        write.assert_called_once_with(written)
        with patch(f"{UC}.env_manager.write_values") as write:
            self.assertEqual(uc.save_camera_settings({}), {})
        write.assert_not_called()

    def test_stream_reachability_validation(self):
        with self.assertRaises(uc.VideoError) as ctx:
            uc.test_stream_reachability("")
        self.assertEqual(str(ctx.exception), "stream_url é obrigatório.")
        with self.assertRaises(uc.VideoError) as ctx:
            uc.test_stream_reachability("rtsp://")
        self.assertEqual(str(ctx.exception), "URL inválida: host não encontrado.")

    def test_stream_reachability_default_port_and_outcomes(self):
        with patch(f"{UC}.socket.create_connection") as conn:
            result = uc.test_stream_reachability("rtsp://cam.local/stream", 3)
        conn.assert_called_once_with(("cam.local", 554), timeout=3)
        self.assertEqual(
            result, {"success": True, "message": "Conexão bem-sucedida com cam.local:554."}
        )
        with patch(f"{UC}.socket.create_connection", side_effect=TimeoutError):
            result = uc.test_stream_reachability("rtmp://cam.local:1936/x")
        self.assertFalse(result["success"])
        self.assertIn("Timeout", result["message"])
        with patch(f"{UC}.socket.create_connection", side_effect=OSError("refused")):
            result = uc.test_stream_reachability("https://cam.local")
        self.assertEqual(result, {"success": False, "message": "Falha na conexão: refused"})
