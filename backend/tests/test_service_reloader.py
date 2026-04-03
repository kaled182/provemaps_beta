from unittest.mock import patch

import os

from setup_app.services.service_reloader import trigger_restart


@patch("setup_app.services.service_reloader.subprocess.run")
def test_trigger_restart_without_commands(mock_run, settings):
    settings.SERVICE_RESTART_COMMANDS = ""
    with patch.dict(os.environ, {"SERVICE_RESTART_COMMANDS": ""}):
        executed = trigger_restart(async_mode=False)

    assert executed is False
    mock_run.assert_not_called()


@patch("setup_app.services.service_reloader.subprocess.run")
def test_trigger_restart_runs_configured_commands(mock_run):
    with patch.dict(os.environ, {"SERVICE_RESTART_COMMANDS": "echo one; echo two"}):
        executed = trigger_restart(async_mode=False)

    assert executed is True
    assert mock_run.call_count == 2
    mock_run.assert_any_call("echo one", shell=True, check=True)
    mock_run.assert_any_call("echo two", shell=True, check=True)


@patch("setup_app.services.service_reloader.subprocess.run")
def test_trigger_restart_accepts_additional_commands(mock_run):
    with patch.dict(os.environ, {"SERVICE_RESTART_COMMANDS": "echo base"}):
        executed = trigger_restart(additional_commands=["echo extra"], async_mode=False)

    assert executed is True
    mock_run.assert_any_call("echo base", shell=True, check=True)
    mock_run.assert_any_call("echo extra", shell=True, check=True)
    assert mock_run.call_count == 2
