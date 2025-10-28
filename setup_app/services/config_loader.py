"""
Runtime configuration loader.
Carrega configurações do banco de dados (FirstTimeSetup)
e as disponibiliza em runtime.
"""
from __future__ import annotations

import os
from typing import Dict

from django.core.cache import cache
from django.db import connection

from setup_app.models import FirstTimeSetup

_CONFIG_CACHE_KEY = "setup_app:runtime_config"
_CONFIG_CACHE_TTL = 300  # 5 minutos


def get_runtime_config() -> Dict[str, str]:
    """
    Obtém a configuração em runtime do cache ou banco de dados.
    Retorna um dicionário com as configurações da aplicação.
    """
    # Tenta buscar do cache primeiro
    cached = cache.get(_CONFIG_CACHE_KEY)
    if cached is not None:
        return cached

    # Se não está no cache, busca do banco
    config = _load_from_database()
    
    # Armazena no cache
    if config:
        cache.set(_CONFIG_CACHE_KEY, config, _CONFIG_CACHE_TTL)
    
    return config


def _load_from_database() -> Dict[str, str]:
    """
    Carrega configurações do banco de dados.
    """
    config = {}
    record = (
        FirstTimeSetup.objects.filter(configured=True)
        .order_by("-configured_at")
        .first()
    )
    if not record:
        return config

    if record.zabbix_url:
        config["ZABBIX_API_URL"] = record.zabbix_url

    if record.auth_type == "token":
        if record.zabbix_api_key:
            config["ZABBIX_API_KEY"] = record.zabbix_api_key
    else:
        if record.zabbix_user:
            config["ZABBIX_API_USER"] = record.zabbix_user
        if record.zabbix_password:
            config["ZABBIX_API_PASSWORD"] = record.zabbix_password

    if record.maps_api_key:
        config["GOOGLE_MAPS_API_KEY"] = record.maps_api_key

    if record.db_host:
        config["DB_HOST"] = record.db_host
    if record.db_port:
        config["DB_PORT"] = record.db_port
    if record.db_name:
        config["DB_NAME"] = record.db_name
    if record.db_user:
        config["DB_USER"] = record.db_user
    if record.db_password:
        config["DB_PASSWORD"] = record.db_password
    if record.redis_url:
        config["REDIS_URL"] = record.redis_url

    return config


def clear_runtime_config_cache():
    """
    Limpa o cache de configuração em runtime.
    Útil após salvar novas configurações.
    """
    cache.delete(_CONFIG_CACHE_KEY)


def get_config_value(key: str, default: str = "") -> str:
    """
    Obtém um valor de configuração específico.
    Prioridade: variável de ambiente > banco de dados > default
    """
    # Primeiro verifica variável de ambiente
    env_value = os.getenv(key)
    if env_value:
        return env_value
    
    # Se não tem na env, busca do banco
    runtime_config = get_runtime_config()
    return runtime_config.get(key, default)


def is_first_time_setup_needed() -> bool:
    """
    Verifica se é necessário fazer o primeiro setup.
    Retorna True se ainda não foi configurado.
    """
    try:
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT TABLE_NAME
                FROM information_schema.TABLES
                WHERE TABLE_SCHEMA = DATABASE()
                AND TABLE_NAME = 'setup_app_firsttimesetup'
            """)
            if not cursor.fetchone():
                return True

            cursor.execute("""
                SELECT COUNT(*)
                FROM setup_app_firsttimesetup
                WHERE configured = 1
            """)
            count = cursor.fetchone()[0]
            return count == 0
    except Exception:
        return True
