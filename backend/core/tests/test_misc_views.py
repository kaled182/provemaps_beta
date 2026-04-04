"""Tests for core.views_spa, core.views_docs, and related simple views."""
from __future__ import annotations

import tempfile
from pathlib import Path

from django.test import RequestFactory, TestCase, override_settings


class SPAViewTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()

    @override_settings(
        GOOGLE_MAPS_API_KEY="AIza-test",
        STATIC_ASSET_VERSION="v1",
        DEBUG=False,
    )
    def test_get_context_data_includes_maps_key(self):
        from core.views_spa import SPAView
        view = SPAView()
        view.request = self.factory.get("/")
        view.kwargs = {}
        view.args = ()
        ctx = view.get_context_data()
        self.assertEqual(ctx["GOOGLE_MAPS_API_KEY"], "AIza-test")

    @override_settings(
        GOOGLE_MAPS_API_KEY="",
        DEBUG=True,
    )
    def test_get_context_data_includes_debug(self):
        from core.views_spa import SPAView
        view = SPAView()
        view.request = self.factory.get("/")
        view.kwargs = {}
        view.args = ()
        ctx = view.get_context_data()
        self.assertTrue(ctx["DEBUG"])

    @override_settings(GOOGLE_MAPS_API_KEY="", STATIC_ASSET_VERSION="test-ver")
    def test_static_asset_version_in_context(self):
        from core.views_spa import SPAView
        view = SPAView()
        view.request = self.factory.get("/")
        view.kwargs = {}
        view.args = ()
        ctx = view.get_context_data()
        self.assertIn("STATIC_ASSET_VERSION", ctx)
        self.assertEqual(ctx["STATIC_ASSET_VERSION"], "test-ver")


class ServeDocFileTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()

    def test_non_md_raises_404(self):
        from core.views_docs import serve_doc_file
        from django.http import Http404
        request = self.factory.get("/docs/test.txt")
        with self.assertRaises(Http404):
            serve_doc_file(request, "test.txt")

    def test_serves_existing_md_file(self):
        from core.views_docs import serve_doc_file
        with tempfile.TemporaryDirectory() as tmpdir:
            doc_dir = Path(tmpdir) / "doc"
            doc_dir.mkdir()
            (doc_dir / "readme.md").write_text("# Hello", encoding="utf-8")
            with override_settings(BASE_DIR=tmpdir):
                request = self.factory.get("/docs/readme.md")
                response = serve_doc_file(request, "readme.md")
        self.assertEqual(response.status_code, 200)
        self.assertIn("# Hello", response.content.decode())

    def test_missing_md_file_raises_404(self):
        from core.views_docs import serve_doc_file
        from django.http import Http404
        with tempfile.TemporaryDirectory() as tmpdir:
            doc_dir = Path(tmpdir) / "doc"
            doc_dir.mkdir()
            with override_settings(BASE_DIR=tmpdir):
                request = self.factory.get("/docs/missing.md")
                with self.assertRaises(Http404):
                    serve_doc_file(request, "missing.md")

    def test_directory_traversal_blocked(self):
        from core.views_docs import serve_doc_file
        from django.http import Http404
        with tempfile.TemporaryDirectory() as tmpdir:
            doc_dir = Path(tmpdir) / "doc"
            doc_dir.mkdir()
            with override_settings(BASE_DIR=tmpdir):
                request = self.factory.get("/docs/../secret.md")
                with self.assertRaises(Http404):
                    serve_doc_file(request, "../secret.md")
