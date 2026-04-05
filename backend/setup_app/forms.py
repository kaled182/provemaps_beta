from __future__ import annotations

import os
import re
from typing import Any

from django import forms
from django.core.exceptions import ValidationError


def validate_db_password(value: str) -> None:
    """Exige senha de banco de dados com complexidade mínima."""
    errors = []
    if len(value) < 12:
        errors.append("mínimo 12 caracteres")
    if not re.search(r"[A-Z]", value):
        errors.append("pelo menos 1 letra maiúscula")
    if not re.search(r"[a-z]", value):
        errors.append("pelo menos 1 letra minúscula")
    if not re.search(r"[0-9]", value):
        errors.append("pelo menos 1 número")
    if not re.search(r"[^A-Za-z0-9]", value):
        errors.append("pelo menos 1 caractere especial (!@#$%...)")
    if errors:
        raise ValidationError(
            f"Senha fraca. Necessário: {', '.join(errors)}."
        )


def _env_default(*keys: str, fallback: str = "") -> str:
    """Return the first non-empty environment value for the provided keys."""
    for key in keys:
        value = os.getenv(key)
        if value:
            return value
    return fallback


class FirstTimeSetupForm(forms.Form):
    company_name = forms.CharField(label="Company name", max_length=255)
    logo = forms.ImageField(label="Company logo (PNG)", required=False)
    zabbix_url = forms.CharField(label="Zabbix URL", max_length=255)
    auth_type = forms.ChoiceField(
        label="Authentication method",
        choices=[("token", "Zabbix API token"), ("login", "Zabbix user and password")],
        widget=forms.RadioSelect,
    )
    zabbix_api_key = forms.CharField(label="Zabbix API key", max_length=255, required=False)
    zabbix_user = forms.CharField(label="Zabbix user", max_length=255, required=False)
    zabbix_password = forms.CharField(
        label="Zabbix password",
        max_length=255,
        required=False,
        widget=forms.PasswordInput,
    )
    map_provider = forms.ChoiceField(
        label="Provedor de mapa",
        choices=[
            ("google", "Google Maps"),
            ("mapbox", "Mapbox"),
            ("osm", "OpenStreetMap (gratuito, sem chave)"),
        ],
        initial="osm",
        widget=forms.RadioSelect,
    )
    maps_api_key = forms.CharField(
        label="Google Maps API key",
        max_length=255,
        required=False,
        help_text="Necessário apenas se usar Google Maps",
    )
    mapbox_token = forms.CharField(
        label="Mapbox Token",
        max_length=512,
        required=False,
        help_text="Necessário apenas se usar Mapbox",
    )
    unique_licence = forms.CharField(label="License key", max_length=255)
    db_host = forms.CharField(
        label="Database host",
        max_length=255,
        initial=_env_default("DB_HOST", "DATABASE_HOST", fallback="postgres"),
    )
    db_port = forms.CharField(
        label="Database port",
        max_length=16,
        initial=_env_default("DB_PORT", "DATABASE_PORT", fallback="5432"),
    )
    db_user = forms.CharField(
        label="Database user",
        max_length=255,
        initial=_env_default("DB_USER", "DATABASE_USER", fallback="app"),
    )
    db_password = forms.CharField(
        label="Database password",
        max_length=255,
        widget=forms.PasswordInput(render_value=True),
        validators=[validate_db_password],
        help_text=(
            "Mínimo 12 caracteres · maiúscula · minúscula"
            " · número · caractere especial"
        ),
    )
    redis_url = forms.CharField(
        label="Redis URL",
        max_length=255,
        initial="redis://redis:6379/1",
        help_text="Example: redis://redis:6379/1",
    )
    domain_name = forms.CharField(
        label="Domain name",
        max_length=255,
        required=False,
        help_text="Optional. Ex: maps.suaempresa.com.br",
    )
    certbot_email = forms.EmailField(
        label="E-mail for SSL notifications",
        required=False,
        help_text="Optional. Used by Let's Encrypt for certificate expiry alerts.",
    )


class EnvConfigForm(forms.Form):
    secret_key = forms.CharField(
        label="SECRET_KEY",
        max_length=255,
        help_text="Restart the server after changing this value.",
    )
    debug = forms.BooleanField(
        label="DEBUG",
        required=False,
        help_text="Disable in production to avoid leaking sensitive information.",
    )
    zabbix_api_url = forms.CharField(label="ZABBIX_API_URL", max_length=255)
    zabbix_api_user = forms.CharField(label="ZABBIX_API_USER", max_length=255, required=False)
    zabbix_api_password = forms.CharField(
        label="ZABBIX_API_PASSWORD",
        max_length=255,
        required=False,
        widget=forms.PasswordInput(render_value=True),
    )
    zabbix_api_key = forms.CharField(
        label="ZABBIX_API_KEY",
        max_length=255,
        required=False,
        help_text="Use when authenticating via API token.",
    )
    google_maps_api_key = forms.CharField(label="GOOGLE_MAPS_API_KEY", max_length=255, required=False)
    allowed_hosts = forms.CharField(
        label="ALLOWED_HOSTS",
        max_length=255,
        required=False,
        help_text="Comma separated. Example: localhost,127.0.0.1,example.com",
    )
    db_host = forms.CharField(label="DB_HOST", max_length=255)
    db_port = forms.CharField(
        label="DB_PORT",
        max_length=16,
        initial=_env_default("DB_PORT", "DATABASE_PORT", fallback="5432"),
    )
    db_name = forms.CharField(label="DB_NAME", max_length=255)
    db_user = forms.CharField(label="DB_USER", max_length=255)
    db_password = forms.CharField(
        label="DB_PASSWORD",
        max_length=255,
        widget=forms.PasswordInput(render_value=True),
    )
    redis_url = forms.CharField(
        label="REDIS_URL",
        max_length=255,
        required=False,
        help_text="Example: redis://redis:6379/1",
    )
    service_restart_commands = forms.CharField(
        label="SERVICE_RESTART_COMMANDS",
        required=False,
        widget=forms.Textarea(attrs={"rows": 3}),
        help_text=(
            "Commands executed after saving credentials. "
            "Separate multiple commands with ';'. Example: "
            "docker compose restart web; docker compose restart worker"
        ),
    )
    enable_diagnostics = forms.BooleanField(
        label="ENABLE_DIAGNOSTIC_ENDPOINTS",
        required=False,
        help_text="Allow diagnostic endpoints (ping/telnet).",
    )

    def clean_allowed_hosts(self) -> str:
        value = self.cleaned_data.get("allowed_hosts", "")
        parts = [host.strip() for host in value.split(",") if host.strip()]
        return ",".join(parts)

    def __init__(self, *args: Any, **kwargs: Any):
        super().__init__(*args, **kwargs)
        base_class = (
            "rounded-lg border border-gray-300 px-3 py-2 text-sm "
            "focus:border-blue-500 focus:outline-none focus:ring "
            "focus:ring-blue-500/20 w-full"
        )
        checkbox_class = (
            "h-4 w-4 text-blue-600 rounded border-gray-300 "
            "focus:ring-blue-500"
        )
        for field in self.fields.values():
            if isinstance(field.widget, forms.CheckboxInput):
                field.widget.attrs.setdefault("class", checkbox_class)
            else:
                field.widget.attrs.setdefault("class", base_class)
