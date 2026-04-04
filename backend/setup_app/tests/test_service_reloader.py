"""Tests for setup_app.services.service_reloader."""
from __future__ import annotations

import os
import subprocess
from unittest.mock import MagicMock, patch

from django.test import TestCase, override_settings


class CollectBaseCommandsTests(TestCase):
    def test_reads_from_env(self):
        from setup_app.services.service_reloader import _collect_base_commands
        with patch.dict(os.environ, {"SERVICE_RESTART_COMMANDS": "cmd1; cmd2"}):
            cmds = _collect_base_commands()
        self.assertEqual(cmds, ["cmd1", "cmd2"])

    def test_falls_back_to_settings(self):
        from setup_app.services.service_reloader import _collect_base_commands
        with patch.dict(os.environ, {}), \
             override_settings(SERVICE_RESTART_COMMANDS="echo hi; echo bye"):
            os.environ.pop("SERVICE_RESTART_COMMANDS", None)  # safe inside patch.dict
            cmds = _collect_base_commands()
        self.assertIsInstance(cmds, list)
        self.assertGreater(len(cmds), 0)

    def test_empty_string_returns_empty_list(self):
        from setup_app.services.service_reloader import _collect_base_commands
        with patch.dict(os.environ, {"SERVICE_RESTART_COMMANDS": ""}), \
             override_settings(SERVICE_RESTART_COMMANDS=""):
            cmds = _collect_base_commands()
        self.assertEqual(cmds, [])

    def test_strips_whitespace_from_commands(self):
        from setup_app.services.service_reloader import _collect_base_commands
        with patch.dict(os.environ, {"SERVICE_RESTART_COMMANDS": "  cmd1  ;  cmd2  "}):
            cmds = _collect_base_commands()
        self.assertEqual(cmds, ["cmd1", "cmd2"])

    def test_ignores_empty_segments(self):
        from setup_app.services.service_reloader import _collect_base_commands
        with patch.dict(os.environ, {"SERVICE_RESTART_COMMANDS": "cmd1;;cmd2"}):
            cmds = _collect_base_commands()
        self.assertEqual(cmds, ["cmd1", "cmd2"])


class TriggerRestartTests(TestCase):
    def test_returns_false_when_no_commands(self):
        from setup_app.services.service_reloader import trigger_restart
        with patch.dict(os.environ, {}), \
             override_settings(SERVICE_RESTART_COMMANDS=""):
            os.environ.pop("SERVICE_RESTART_COMMANDS", None)  # safe inside patch.dict
            result = trigger_restart()
        self.assertFalse(result)

    def test_returns_true_when_commands_exist(self):
        from setup_app.services.service_reloader import trigger_restart
        with patch.dict(os.environ, {"SERVICE_RESTART_COMMANDS": "echo hi"}), \
             patch("setup_app.services.service_reloader.threading.Thread") as mock_thread:
            mock_thread.return_value = MagicMock()
            result = trigger_restart()
        self.assertTrue(result)

    def test_async_mode_starts_thread(self):
        from setup_app.services.service_reloader import trigger_restart
        with patch.dict(os.environ, {"SERVICE_RESTART_COMMANDS": "echo hi"}), \
             patch("setup_app.services.service_reloader.threading.Thread") as mock_thread:
            instance = MagicMock()
            mock_thread.return_value = instance
            trigger_restart(async_mode=True)
        instance.start.assert_called_once()

    def test_sync_mode_calls_run_commands(self):
        from setup_app.services.service_reloader import trigger_restart
        with patch.dict(os.environ, {"SERVICE_RESTART_COMMANDS": "echo hi"}), \
             patch("setup_app.services.service_reloader._run_commands") as mock_run:
            trigger_restart(async_mode=False)
        mock_run.assert_called_once()

    def test_additional_commands_are_included(self):
        from setup_app.services.service_reloader import trigger_restart
        with patch.dict(os.environ, {}), \
             override_settings(SERVICE_RESTART_COMMANDS=""), \
             patch("setup_app.services.service_reloader._run_commands") as mock_run:
            os.environ.pop("SERVICE_RESTART_COMMANDS", None)
            trigger_restart(additional_commands=["extra cmd"], async_mode=False)
        mock_run.assert_called_once_with(["extra cmd"])

    def test_empty_additional_commands_ignored(self):
        from setup_app.services.service_reloader import trigger_restart
        with patch.dict(os.environ, {"SERVICE_RESTART_COMMANDS": "base cmd"}), \
             patch("setup_app.services.service_reloader._run_commands") as mock_run:
            trigger_restart(additional_commands=["", None], async_mode=False)
        args = mock_run.call_args[0][0]
        self.assertIn("base cmd", args)
        self.assertNotIn("", args)


class RunCommandsTests(TestCase):
    def test_runs_each_command(self):
        from setup_app.services.service_reloader import _run_commands
        with patch("setup_app.services.service_reloader.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0)
            _run_commands(["cmd1", "cmd2"])
        self.assertEqual(mock_run.call_count, 2)

    def test_logs_error_on_called_process_error(self):
        from setup_app.services.service_reloader import _run_commands
        with patch("setup_app.services.service_reloader.subprocess.run") as mock_run:
            mock_run.side_effect = subprocess.CalledProcessError(1, "bad_cmd")
            _run_commands(["bad_cmd"])  # should not raise

    def test_logs_error_on_unexpected_exception(self):
        from setup_app.services.service_reloader import _run_commands
        with patch("setup_app.services.service_reloader.subprocess.run") as mock_run:
            mock_run.side_effect = OSError("permission denied")
            _run_commands(["cmd"])  # should not raise
