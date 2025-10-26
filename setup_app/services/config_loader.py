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
    Usa SQL direto para evitar problemas de import circular.
    """
    config = {}
    
    try:
        # Verifica se a tabela existe
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT TABLE_NAME
                FROM information_schema.TABLES
                WHERE TABLE_SCHEMA = DATABASE()
                AND TABLE_NAME = 'setup_app_firsttimesetup'
            """)
            if not cursor.fetchone():
                return config

            # Busca a configuração mais recente
            cursor.execute("""
                SELECT
                    zabbix_url,
                    auth_type,
                    zabbix_api_key,
                    zabbix_user,
                    zabbix_password,
                    maps_api_key
                FROM setup_app_firsttimesetup
                WHERE configured = 1
                ORDER BY configured_at DESC
                LIMIT 1
            """)
            
            row = cursor.fetchone()
            if row:
                zabbix_url, auth_type, api_key, user, password, maps_key = row

                if zabbix_url:
                    config['ZABBIX_API_URL'] = zabbix_url

                if auth_type == 'token' and api_key:
                    config['ZABBIX_API_KEY'] = api_key
                elif auth_type == 'login':
                    if user:
                        config['ZABBIX_API_USER'] = user
                    if password:
                        config['ZABBIX_API_PASSWORD'] = password

                if maps_key:
                    config['GOOGLE_MAPS_API_KEY'] = maps_key

    except Exception:
        # Se houver erro (tabela não existe, etc), retorna config vazio
        pass

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
