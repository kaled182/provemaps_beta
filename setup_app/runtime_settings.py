"""
Runtime settings override.
Permite sobrescrever configurações do Django em runtime
baseado nos dados salvos no banco de dados.
"""
from __future__ import annotations

import functools
from typing import Any

from django.conf import settings as django_settings

from .services.config_loader import get_config_value, get_runtime_config


@functools.lru_cache(maxsize=1)
def _get_cached_config():
    """Cache da configuração em runtime."""
    return get_runtime_config()


class RuntimeSettings:
    """
    Wrapper para acessar configurações com fallback para banco de dados.
    """

    def __getattr__(self, name: str) -> Any:
        """
        Busca configuração com prioridade:
        1. Django settings (variáveis de ambiente)
        2. Banco de dados (FirstTimeSetup)
        3. None
        """
        # Primeiro tenta pegar do Django settings
        django_value = getattr(django_settings, name, None)
        if django_value:
            return django_value

        # Se não tem no Django settings, busca do banco
        runtime_config = _get_cached_config()
        return runtime_config.get(name)

    def reload_config(self):
        """Limpa cache e força recarregamento."""
        _get_cached_config.cache_clear()


# Instância global para uso em todo o projeto
runtime_settings = RuntimeSettings()


# Funções auxiliares para acessar configurações específicas
def get_zabbix_url() -> str:
    """Obtém URL do Zabbix."""
    return get_config_value('ZABBIX_API_URL', '')


def get_zabbix_api_key() -> str:
    """Obtém API Key do Zabbix (se auth_type='token')."""
    return get_config_value('ZABBIX_API_KEY', '')


def get_zabbix_user() -> str:
    """Obtém usuário do Zabbix (se auth_type='login')."""
    return get_config_value('ZABBIX_API_USER', '')


def get_zabbix_password() -> str:
    """Obtém senha do Zabbix (se auth_type='login')."""
    return get_config_value('ZABBIX_API_PASSWORD', '')


def get_google_maps_api_key() -> str:
    """Obtém API Key do Google Maps."""
    return get_config_value('GOOGLE_MAPS_API_KEY', '')
