"""Tests for maps_view.views."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from django.test import RequestFactory, TestCase, override_settings


class BuildDashboardEventPayloadTests(TestCase):
    def test_returns_result_of_build_dashboard_payload(self):
        from maps_view.views import build_dashboard_event_payload

        with (
            patch("maps_view.views.get_hosts_status_data", return_value={"hosts": []}),
            patch(
                "maps_view.views.build_dashboard_payload", return_value={"event": "ok"}
            ) as mock_bdp,
        ):
            result = build_dashboard_event_payload()
        self.assertEqual(result, {"event": "ok"})
        mock_bdp.assert_called_once_with({"hosts": []})


class DashboardWithHostsStatusTests(TestCase):
    def test_calls_get_hosts_status_data(self):
        from maps_view.views import dashboard_with_hosts_status

        with patch("maps_view.views.get_hosts_status_data", return_value={"ok": True}) as mock_fn:
            result = dashboard_with_hosts_status()
        mock_fn.assert_called_once()
        self.assertEqual(result, {"ok": True})


class DashboardViewTests(TestCase):
    """EV-0079: sem legado nem canário — o dashboard é sempre o SPA."""

    def setUp(self):
        self.factory = RequestFactory()

    def _render(self, maps_key=""):
        from maps_view.views import dashboard_view

        request = self.factory.get("/")
        mock_config = MagicMock()
        mock_config.google_maps_api_key = maps_key
        with (
            patch("maps_view.views.runtime_settings") as mock_rs,
            patch("maps_view.views.render") as mock_render,
        ):
            mock_rs.get_runtime_config.return_value = mock_config
            mock_render.return_value = MagicMock(status_code=200)
            dashboard_view(request)
        return mock_render.call_args[0]

    def test_always_serves_spa(self):
        self.assertEqual(self._render()[1], "spa.html")

    @override_settings(USE_VUE_DASHBOARD=False, VUE_DASHBOARD_ROLLOUT_PERCENTAGE=0)
    def test_old_flags_no_longer_bring_back_the_legacy_dashboard(self):
        self.assertEqual(self._render()[1], "spa.html")

    def test_context_includes_maps_key(self):
        self.assertEqual(self._render("MY_MAPS_KEY")[2]["GOOGLE_MAPS_API_KEY"], "MY_MAPS_KEY")

    def test_legacy_template_is_gone(self):
        from django.template import TemplateDoesNotExist
        from django.template.loader import get_template

        with self.assertRaises(TemplateDoesNotExist):
            get_template("dashboard.html")


class MetricsDashboardViewTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()

    def _make_request(self, url="/metrics-dashboard/", query=""):
        path = f"{url}?q={query}" if query else url
        request = self.factory.get(path)
        request.user = MagicMock(is_authenticated=True)
        return request

    def test_renders_metrics_template(self):
        from maps_view.views import metrics_dashboard

        request = self._make_request()
        metrics_output = b"# HELP my_metric A metric\n# TYPE my_metric gauge\nmy_metric 1\n"
        with (
            patch("maps_view.views.generate_latest", return_value=metrics_output),
            patch("maps_view.views.render") as mock_render,
        ):
            mock_render.return_value = MagicMock(status_code=200)
            metrics_dashboard(request)
        template = mock_render.call_args[0][1]
        self.assertEqual(template, "metrics_dashboard.html")

    def test_filters_metrics_by_query(self):
        from maps_view.views import metrics_dashboard

        request = self._make_request(query="my_metric")
        metrics_output = (
            b"# HELP my_metric A metric\n"
            b"# TYPE my_metric gauge\n"
            b"my_metric 1\n"
            b"# HELP other_metric Another\n"
            b"# TYPE other_metric counter\n"
            b"other_metric 5\n"
        )
        with (
            patch("maps_view.views.generate_latest", return_value=metrics_output),
            patch("maps_view.views.render") as mock_render,
        ):
            mock_render.return_value = MagicMock(status_code=200)
            metrics_dashboard(request)
        ctx = mock_render.call_args[0][2]
        metric_names = [m["name"] for m in ctx["metrics"]]
        self.assertIn("my_metric", metric_names)
        self.assertNotIn("other_metric", metric_names)

    def test_empty_query_returns_all_metrics(self):
        from maps_view.views import metrics_dashboard

        request = self._make_request()
        metrics_output = (
            b"# HELP metric_a First\n# TYPE metric_a gauge\nmetric_a 1\n"
            b"# HELP metric_b Second\n# TYPE metric_b gauge\nmetric_b 2\n"
        )
        with (
            patch("maps_view.views.generate_latest", return_value=metrics_output),
            patch("maps_view.views.render") as mock_render,
        ):
            mock_render.return_value = MagicMock(status_code=200)
            metrics_dashboard(request)
        ctx = mock_render.call_args[0][2]
        self.assertEqual(len(ctx["metrics"]), 2)

    def test_context_has_metrics_source_url(self):
        from maps_view.views import metrics_dashboard

        request = self._make_request()
        request.build_absolute_uri = lambda path: f"http://testserver{path}"
        with (
            patch("maps_view.views.generate_latest", return_value=b""),
            patch("maps_view.views.render") as mock_render,
        ):
            mock_render.return_value = MagicMock(status_code=200)
            metrics_dashboard(request)
        ctx = mock_render.call_args[0][2]
        self.assertIn("metrics_source_url", ctx)
