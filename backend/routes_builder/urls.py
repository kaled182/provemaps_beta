"""URL definitions for the routes_builder app."""

from django.urls import path, include
from . import views
from . import views_tasks

app_name = "routes_builder"

# --- Administrative task endpoints ---
task_urlpatterns = [
    path(
        "build/",
        views_tasks.enqueue_build_route,
        name="enqueue_build_route",
    ),
    path(
        "batch/",
        views_tasks.enqueue_build_routes_batch,
        name="enqueue_build_routes_batch",
    ),
    path(
        "import/",
        views_tasks.enqueue_import_route,
        name="enqueue_import_route",
    ),
    path(
        "invalidate/",
        views_tasks.enqueue_invalidate_route_cache,
        name="enqueue_invalidate_route_cache",
    ),
    path(
        "health/",
        views_tasks.enqueue_health_check,
        name="enqueue_health_check",
    ),
    path(
        "status/<str:task_id>/",
        views_tasks.task_status,
        name="task_status",
    ),
    path(
        "bulk/",
        views_tasks.enqueue_bulk_operations,
        name="enqueue_bulk_operations",
    ),
]

urlpatterns = [
    # --- Public UI ---
    path(
        "fiber-route-builder/",
        views.fiber_route_builder_view,
        name="fiber_route_builder",
    ),

    # --- Administrative API (tasks) ---
    path("tasks/", include((task_urlpatterns, "tasks"))),
]
