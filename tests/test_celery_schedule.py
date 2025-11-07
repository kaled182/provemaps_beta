import os

os.environ.setdefault("CELERY_TASK_ALWAYS_EAGER", "true")

from core.celery import app  # noqa: E402


def test_dashboard_cache_refresh_scheduled():
    schedule = app.conf.beat_schedule
    assert "refresh-dashboard-cache" in schedule
    entry = schedule["refresh-dashboard-cache"]
    assert entry["task"] == "monitoring.tasks.refresh_dashboard_cache_task"


def test_inventory_sync_scheduled():
    schedule = app.conf.beat_schedule
    assert "sync-zabbix-inventory" in schedule
    entry = schedule["sync-zabbix-inventory"]
    assert entry["task"] == "inventory.tasks.sync_zabbix_inventory_task"
    assert entry["schedule"] > 0
