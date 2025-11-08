import tempfile
from pathlib import Path

from django.test import TestCase

from setup_app.utils import env_manager


class EnvManagerTests(TestCase):
    def setUp(self):
        self.original_path = env_manager.ENV_PATH
        self.temp_dir = tempfile.TemporaryDirectory()
        self.temp_path = Path(self.temp_dir.name) / ".env"
        env_manager.ENV_PATH = self.temp_path

    def tearDown(self):
        env_manager.ENV_PATH = self.original_path
        self.temp_dir.cleanup()

    def test_write_and_read_values(self):
        env_manager.write_values({"TEST_KEY": "value", "DEBUG": "True"})
        data = env_manager.read_env()
        self.assertEqual(data.get("TEST_KEY"), "value")
        self.assertEqual(data.get("DEBUG"), "True")

        env_manager.write_values({"TEST_KEY": "updated"})
        data = env_manager.read_env()
        self.assertEqual(data.get("TEST_KEY"), "updated")
        self.assertEqual(data.get("DEBUG"), "True")

