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
        pass
