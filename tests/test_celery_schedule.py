import os

os.environ.setdefault("CELERY_TASK_ALWAYS_EAGER", "true")

from core.celery import app  # noqa: E402


def test_dashboard_cache_refresh_scheduled():
    schedule = app.conf.beat_schedule
    assert "refresh-dashboard-cache" in schedule
    entry = schedule["refresh-dashboard-cache"]
    assert entry["task"] == "maps_view.tasks.refresh_dashboard_cache_task"
