"""Tests for setup_app.context_processors."""
from __future__ import annotations

import json
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from django.test import RequestFactory, TestCase, override_settings


class SetupLogoContextProcessorTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.request = self.factory.get("/")

    def test_returns_company_logo_when_profile_has_logo(self):
        from setup_app.context_processors import setup_logo
        mock_profile = MagicMock()
        mock_profile.assets_logo = "logos/company.png"
        with patch(
            "setup_app.context_processors.CompanyProfile.objects"
            ".order_by"
        ) as mock_order:
            mock_order.return_value.first.return_value = mock_profile
            result = setup_logo(self.request)
        self.assertIn("setup_logo", result)
        self.assertEqual(result["setup_logo"].logo, "logos/company.png")

    def test_returns_first_time_setup_when_no_profile_logo(self):
        from setup_app.context_processors import setup_logo
        mock_profile = MagicMock()
        mock_profile.assets_logo = None
        mock_setup = MagicMock()
        with patch(
            "setup_app.context_processors.CompanyProfile.objects"
            ".order_by"
        ) as mock_profile_order, patch(
            "setup_app.context_processors.FirstTimeSetup.objects"
            ".filter"
        ) as mock_fts_filter:
            mock_profile_order.return_value.first.return_value = mock_profile
            mock_fts_filter.return_value.order_by.return_value.first.return_value = mock_setup
            result = setup_logo(self.request)
        self.assertEqual(result["setup_logo"], mock_setup)

    def test_returns_none_dict_when_no_profile(self):
        from setup_app.context_processors import setup_logo
        mock_setup = MagicMock()
        with patch(
            "setup_app.context_processors.CompanyProfile.objects"
            ".order_by"
        ) as mock_order, patch(
            "setup_app.context_processors.FirstTimeSetup.objects"
            ".filter"
        ) as mock_fts_filter:
            mock_order.return_value.first.return_value = None
            mock_fts_filter.return_value.order_by.return_value.first.return_value = mock_setup
            result = setup_logo(self.request)
        self.assertEqual(result["setup_logo"], mock_setup)


class StaticVersionContextProcessorTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.request = self.factory.get("/")

    @override_settings(STATIC_ASSET_VERSION="v42")
    def test_exposes_static_asset_version(self):
        from setup_app.context_processors import static_version
        with patch("setup_app.context_processors._load_vite_entry", return_value=None):
            result = static_version(self.request)
        self.assertEqual(result["STATIC_ASSET_VERSION"], "v42")

    def test_exposes_vite_entry(self):
        from setup_app.context_processors import static_version
        entry = {"file": "assets/main.js", "css": ["assets/main.css"]}
        with patch(
            "setup_app.context_processors._load_vite_entry", return_value=entry
        ):
            result = static_version(self.request)
        self.assertEqual(result["VITE_ENTRY"], entry)


class LoadViteEntryTests(TestCase):
    def test_returns_none_when_manifest_missing(self):
        from setup_app.context_processors import _load_vite_entry
        import setup_app.context_processors as cp
        cp._vite_manifest_cache["mtime"] = None
        cp._vite_manifest_cache["entry"] = None
        with tempfile.TemporaryDirectory() as tmpdir:
            with override_settings(STATIC_ROOT=tmpdir):
                result = _load_vite_entry()
        self.assertIsNone(result)

    def test_reads_valid_manifest(self):
        from setup_app.context_processors import _load_vite_entry
        import setup_app.context_processors as cp
        cp._vite_manifest_cache["mtime"] = None
        cp._vite_manifest_cache["entry"] = None

        manifest = {
            "index.html": {
                "file": "assets/main.abc123.js",
                "css": ["assets/main.abc123.css"],
            }
        }
        with tempfile.TemporaryDirectory() as tmpdir:
            manifest_dir = Path(tmpdir) / "vue-spa" / ".vite"
            manifest_dir.mkdir(parents=True)
            (manifest_dir / "manifest.json").write_text(
                json.dumps(manifest), encoding="utf-8"
            )
            with override_settings(STATIC_ROOT=tmpdir):
                result = _load_vite_entry()

        self.assertIsNotNone(result)
        self.assertEqual(result["file"], "assets/main.abc123.js")

    def test_returns_cached_entry_when_mtime_unchanged(self):
        from setup_app.context_processors import _load_vite_entry
        import setup_app.context_processors as cp

        with tempfile.TemporaryDirectory() as tmpdir:
            manifest_dir = Path(tmpdir) / "vue-spa" / ".vite"
            manifest_dir.mkdir(parents=True)
            manifest_path = manifest_dir / "manifest.json"
            manifest_path.write_text(
                json.dumps(
                    {"index.html": {"file": "cached.js", "css": []}}
                ),
                encoding="utf-8",
            )
            stat = manifest_path.stat()
            cp._vite_manifest_cache["mtime"] = stat.st_mtime
            cp._vite_manifest_cache["entry"] = {"file": "cached.js", "css": []}

            with override_settings(STATIC_ROOT=tmpdir):
                result = _load_vite_entry()

        self.assertEqual(result["file"], "cached.js")

    def test_returns_none_on_invalid_json(self):
        from setup_app.context_processors import _load_vite_entry
        import setup_app.context_processors as cp
        cp._vite_manifest_cache["mtime"] = None
        cp._vite_manifest_cache["entry"] = None

        with tempfile.TemporaryDirectory() as tmpdir:
            manifest_dir = Path(tmpdir) / "vue-spa" / ".vite"
            manifest_dir.mkdir(parents=True)
            (manifest_dir / "manifest.json").write_text(
                "not valid json", encoding="utf-8"
            )
            with override_settings(STATIC_ROOT=tmpdir):
                result = _load_vite_entry()

        self.assertIsNone(result)

    def test_returns_none_when_no_file_key_in_entry(self):
        from setup_app.context_processors import _load_vite_entry
        import setup_app.context_processors as cp
        cp._vite_manifest_cache["mtime"] = None
        cp._vite_manifest_cache["entry"] = None

        with tempfile.TemporaryDirectory() as tmpdir:
            manifest_dir = Path(tmpdir) / "vue-spa" / ".vite"
            manifest_dir.mkdir(parents=True)
            (manifest_dir / "manifest.json").write_text(
                json.dumps({"index.html": {"css": []}}),
                encoding="utf-8",
            )
            with override_settings(STATIC_ROOT=tmpdir):
                result = _load_vite_entry()

        self.assertIsNone(result)
