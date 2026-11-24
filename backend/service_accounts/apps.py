from django.apps import AppConfig


class ServiceAccountsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "service_accounts"
    verbose_name = "Service Accounts"

    def ready(self) -> None:
        # EV-0098: regista a descrição OpenAPI do token de conta de serviço.
        from . import schema  # noqa: F401
