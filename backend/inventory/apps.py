from django.apps import AppConfig


class InventoryConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "inventory"
    verbose_name = "Network Inventory"

    def ready(self):
        """
        Initialize app-specific configurations.
        Import signals or perform startup tasks here if needed.
        """
        # Ensure route-related models register under the inventory app.
        try:
            import importlib

            importlib.import_module("inventory.models_routes")
            importlib.import_module("inventory.signals_spatial")
        except ImportError:
            # The module may be absent in certain stripped-down runtimes.
            return
