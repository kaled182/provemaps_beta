import tempfile
from pathlib import Path

from io import StringIO
from unittest.mock import MagicMock, patch

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.test import Client, override_settings, TestCase
from django.urls import reverse

from setup_app.models import FirstTimeSetup
from setup_app.services import runtime_settings
from setup_app.utils import env_manager
from zabbix_api.guards import reload_diagnostics_flag_cache


class RuntimeSettingsTests(TestCase):
    def setUp(self):
        runtime_settings.reload_config()

    def tearDown(self):
        runtime_settings.reload_config()

    def test_fallback_uses_settings(self):
        config = runtime_settings.get_runtime_config()
        from django.conf import settings

        self.assertEqual(config.zabbix_api_url, settings.ZABBIX_API_URL)
        self.assertEqual(config.google_maps_api_key, settings.GOOGLE_MAPS_API_KEY)

    @override_settings(ENABLE_DIAGNOSTIC_ENDPOINTS=True)
    def test_diagnostics_flag_uses_settings(self):
        runtime_settings.reload_config()
        config = runtime_settings.get_runtime_config()
        self.assertTrue(config.diagnostics_enabled)

    def test_runtime_reads_database_record(self):
        FirstTimeSetup.objects.create(
            company_name="ACME",
            zabbix_url="http://zabbix.local/api_jsonrpc.php",
            auth_type="login",
            zabbix_user="admin",
            zabbix_password="pwd",
            maps_api_key="maps-123",
            unique_licence="licence-1",
            db_host="db.internal",
            db_port="3306",
            db_name="mapspro_db",
            db_user="maps_user",
            db_password="maps_pass",
            redis_url="redis://redis.internal:6379/1",
            configured=True,
        )
        runtime_settings.reload_config()
        config = runtime_settings.get_runtime_config()
        self.assertEqual(config.zabbix_api_url, "http://zabbix.local/api_jsonrpc.php")
        self.assertEqual(config.zabbix_api_user, "admin")
        self.assertEqual(config.google_maps_api_key, "maps-123")
        self.assertEqual(config.db_host, "db.internal")
        self.assertEqual(config.db_name, "mapspro_db")
        self.assertEqual(config.db_user, "maps_user")
        self.assertEqual(config.redis_url, "redis://redis.internal:6379/1")


class ManageEnvironmentViewTests(TestCase):
    def setUp(self):
        self.tmp_dir = tempfile.TemporaryDirectory()
        self.original_env_path = env_manager.ENV_PATH
        env_manager.ENV_PATH = Path(self.tmp_dir.name) / ".env"
        env_manager.ENV_PATH.write_text("SECRET_KEY=abc\nDEBUG=True\n", encoding="utf-8")
        FirstTimeSetup.objects.create(
            company_name="Configured Corp",
            zabbix_url="http://example.com/api_jsonrpc.php",
            auth_type="token",
            zabbix_api_key="initial",
            configured=True,
        )

        self.client = Client()
        User = get_user_model()
        self.user = User.objects.create_user("staff", password="pass", is_staff=True)
        self.client.force_login(self.user)

    def tearDown(self):
        env_manager.ENV_PATH = self.original_env_path
        self.tmp_dir.cleanup()
        runtime_settings.reload_config()

    def test_get_manage_environment(self):
        response = self.client.get(reverse("setup_app:manage_environment"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "System Settings")

    def test_post_updates_env_and_reload(self):
        payload = {
            "secret_key": "new-secret",
            "debug": "on",
            "zabbix_api_url": "http://example/api_jsonrpc.php",
            "zabbix_api_user": "user",
            "zabbix_api_password": "password",
            "zabbix_api_key": "",
            "google_maps_api_key": "maps-key",
            "allowed_hosts": "localhost,127.0.0.1",
            "enable_diagnostics": "on",
            "db_host": "db.local",
            "db_port": "3307",
            "db_name": "maps_db",
            "db_user": "maps_user",
            "db_password": "maps_pass",
            "redis_url": "redis://redis:6379/2",
            "service_restart_commands": "",
        }
        response = self.client.post(reverse("setup_app:manage_environment"), data=payload)
        self.assertEqual(response.status_code, 302)
        content = env_manager.read_env()
        self.assertEqual(content["SECRET_KEY"], "new-secret")
        self.assertEqual(content["ZABBIX_API_URL"], "http://example/api_jsonrpc.php")
        self.assertEqual(content["ENABLE_DIAGNOSTIC_ENDPOINTS"], "True")
        self.assertEqual(content["DB_HOST"], "db.local")
        self.assertEqual(content["DB_PORT"], "3307")
        self.assertEqual(content["REDIS_URL"], "redis://redis:6379/2")
        self.assertEqual(content.get("SERVICE_RESTART_COMMANDS", ""), "")

    def test_non_staff_redirects(self):
        User = get_user_model()
        non_staff = User.objects.create_user("basic", password="pass")
        self.client.logout()
        self.client.force_login(non_staff)
        response = self.client.get(reverse("setup_app:manage_environment"))
        self.assertEqual(response.status_code, 302)


class DiagnosticsEndpointsTests(TestCase):
    def setUp(self):
        self.tmp_dir = tempfile.TemporaryDirectory()
        self.original_env_path = env_manager.ENV_PATH
        env_manager.ENV_PATH = Path(self.tmp_dir.name) / ".env"
        env_manager.ENV_PATH.write_text("ENABLE_DIAGNOSTIC_ENDPOINTS=False\n", encoding="utf-8")
        runtime_settings.reload_config()
        reload_diagnostics_flag_cache()
        FirstTimeSetup.objects.create(
            company_name="Configured Corp",
            zabbix_url="http://example.com/api_jsonrpc.php",
            auth_type="token",
            zabbix_api_key="initial",
            configured=True,
        )
        User = get_user_model()
        self.staff = User.objects.create_user("diag-staff", password="pass", is_staff=True)
        self.client = Client()

    def tearDown(self):
        env_manager.ENV_PATH = self.original_env_path
        self.tmp_dir.cleanup()
        runtime_settings.reload_config()
        reload_diagnostics_flag_cache()

    def test_requires_authentication(self):
        response = self.client.get(reverse("zabbix_api:api_test_ping"))
        self.assertEqual(response.status_code, 302)

    def test_requires_toggle(self):
        self.client.force_login(self.staff)
        response = self.client.get(reverse("zabbix_api:api_test_ping"), {"ip": "127.0.0.1"})
        self.assertEqual(response.status_code, 403)

    def test_allows_when_enabled(self):
        env_manager.write_values({"ENABLE_DIAGNOSTIC_ENDPOINTS": "True"})
        runtime_settings.reload_config()
        self.client.force_login(self.staff)
        with patch("zabbix_api.diagnostics.subprocess.run") as mock_run, patch(
            "zabbix_api.diagnostics.platform.system", return_value="linux"
        ):
            mock_run.return_value = MagicMock(
                returncode=0,
                stdout="1 packets transmitted, 1 received, 0% packet loss\n"
                "rtt min/avg/max/mdev = 0.1/0.1/0.1/0.0 ms",
            )
            response = self.client.get(reverse("zabbix_api:api_test_ping"), {"ip": "127.0.0.1"})
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.json()["status"], "success")


class GenerateFernetKeyCommandTests(TestCase):
    def setUp(self):
        self.tmp_dir = tempfile.TemporaryDirectory()
        self.original_env_path = env_manager.ENV_PATH
        env_manager.ENV_PATH = Path(self.tmp_dir.name) / ".env"

    def tearDown(self):
        env_manager.ENV_PATH = self.original_env_path
        self.tmp_dir.cleanup()

    def test_prints_key(self):
        out = StringIO()
        call_command("generate_fernet_key", stdout=out)
        key = out.getvalue().strip()
        self.assertEqual(len(key), 44)

    def test_write_key(self):
        out = StringIO()
        call_command("generate_fernet_key", "--write", "--force", stdout=out)
        env_data = env_manager.read_env()
        self.assertEqual(len(env_data.get("FERNET_KEY", "")), 44)
