"""Django app config for 'core' app."""
from django.apps import AppConfig


class CoreConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "core"

    def ready(self) -> None:
        """Initialize Prometheus metrics on Django startup."""
        # Import here to avoid AppRegistryNotReady
        from core.metrics_static_version import init_static_version_metric
        from core.metrics_custom import init_metrics
        from core.metrics_feature_flags import collect_feature_flags

        init_static_version_metric()
        init_metrics()
        collect_feature_flags()
