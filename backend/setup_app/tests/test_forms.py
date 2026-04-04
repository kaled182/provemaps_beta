"""Tests for setup_app.forms — FirstTimeSetupForm, EnvConfigForm, _env_default."""
from __future__ import annotations

import os
from unittest.mock import patch

from django.test import TestCase


class EnvDefaultTests(TestCase):
    def test_returns_first_non_empty_env_value(self):
        from setup_app.forms import _env_default
        with patch.dict(os.environ, {"KEY_A": "", "KEY_B": "found"}):
            result = _env_default("KEY_A", "KEY_B", fallback="default")
        self.assertEqual(result, "found")

    def test_returns_fallback_when_all_missing(self):
        from setup_app.forms import _env_default
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("MISSING_KEY_XYZ", None)
            result = _env_default("MISSING_KEY_XYZ", fallback="mydefault")
        self.assertEqual(result, "mydefault")

    def test_returns_empty_fallback_when_no_fallback_given(self):
        from setup_app.forms import _env_default
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("MISSING_KEY_ABC", None)
            result = _env_default("MISSING_KEY_ABC")
        self.assertEqual(result, "")


class EnvConfigFormTests(TestCase):
    def _make_form(self, **overrides):
        data = {
            "secret_key": "test-secret",
            "debug": False,
            "zabbix_api_url": "http://zabbix.local",
            "zabbix_api_user": "",
            "zabbix_api_password": "",
            "zabbix_api_key": "",
            "google_maps_api_key": "",
            "allowed_hosts": "localhost,127.0.0.1",
            "db_host": "localhost",
            "db_port": "5432",
            "db_name": "testdb",
            "db_user": "postgres",
            "db_password": "secret",
            "redis_url": "redis://localhost:6379/1",
            "service_restart_commands": "",
            "enable_diagnostics": False,
        }
        data.update(overrides)
        return data

    def test_valid_form_is_valid(self):
        from setup_app.forms import EnvConfigForm
        form = EnvConfigForm(data=self._make_form())
        self.assertTrue(form.is_valid(), form.errors)

    def test_missing_required_field_is_invalid(self):
        from setup_app.forms import EnvConfigForm
        data = self._make_form()
        del data["secret_key"]
        form = EnvConfigForm(data=data)
        self.assertFalse(form.is_valid())
        self.assertIn("secret_key", form.errors)

    def test_clean_allowed_hosts_strips_whitespace(self):
        from setup_app.forms import EnvConfigForm
        data = self._make_form(allowed_hosts=" localhost , 127.0.0.1 , ")
        form = EnvConfigForm(data=data)
        self.assertTrue(form.is_valid(), form.errors)
        self.assertEqual(form.cleaned_data["allowed_hosts"], "localhost,127.0.0.1")

    def test_clean_allowed_hosts_empty_string(self):
        from setup_app.forms import EnvConfigForm
        data = self._make_form(allowed_hosts="")
        form = EnvConfigForm(data=data)
        self.assertTrue(form.is_valid(), form.errors)
        self.assertEqual(form.cleaned_data["allowed_hosts"], "")

    def test_form_fields_have_css_classes(self):
        from setup_app.forms import EnvConfigForm
        form = EnvConfigForm()
        for field in form.fields.values():
            self.assertIn("class", field.widget.attrs)


class FirstTimeSetupFormTests(TestCase):
    def test_form_is_importable(self):
        from setup_app.forms import FirstTimeSetupForm
        form = FirstTimeSetupForm()
        self.assertIn("company_name", form.fields)
        self.assertIn("zabbix_url", form.fields)
        self.assertIn("auth_type", form.fields)

    def test_auth_type_choices(self):
        from setup_app.forms import FirstTimeSetupForm
        form = FirstTimeSetupForm()
        choices = dict(form.fields["auth_type"].choices)
        self.assertIn("token", choices)
        self.assertIn("login", choices)

    def test_db_host_field_exists(self):
        from setup_app.forms import FirstTimeSetupForm
        form = FirstTimeSetupForm()
        self.assertIn("db_host", form.fields)
