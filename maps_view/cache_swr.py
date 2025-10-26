"""
Cache SWR (Stale-While-Revalidate) para Dashboard.

Estratégia:
1. Serve dados stale do cache imediatamente (resposta rápida)
2. Dispara revalidação em background via Celery task
3. Frontend exibe banner de "dados desatualizados" com timestamp

Features:
- TTL: 5 minutos (dados frescos)
- Stale TTL: 30 minutos (serve stale se cache expirou mas ainda disponível)
- Background refresh via Celery
- Fallback para fetch síncrono se cache totalmente vazio
"""

import logging
import time
from typing import Any, Callable, Dict, Optional

from django.core.cache import cache
from django.conf import settings

logger = logging.getLogger(__name__)

# Configurações SWR - Reduzido para monitoramento em tempo real
SWR_FRESH_TTL = getattr(settings, "SWR_FRESH_TTL", 30)  # 30 segundos (fresh)
SWR_STALE_TTL = getattr(settings, "SWR_STALE_TTL", 60)  # 1 min (stale)
SWR_ENABLED = getattr(settings, "SWR_ENABLED", True)


class SWRCache:
    """
    Cache com padrão Stale-While-Revalidate.
    
    Exemplo:
        cache_swr = SWRCache(key="dashboard:hosts")
        data = cache_swr.get_or_fetch(
            fetch_fn=lambda: get_hosts_status_data(),
            async_task=refresh_dashboard_cache_task.delay
        )
    """

    def __init__(
        self,
        key: str,
        fresh_ttl: int = SWR_FRESH_TTL,
        stale_ttl: int = SWR_STALE_TTL,
    ):
        """
        Args:
            key: Cache key único
            fresh_ttl: Tempo (segundos) que dados são considerados frescos
            stale_ttl: Tempo (segundos) que dados stale ainda podem ser servidos
        """
        self.key = key
        self.fresh_ttl = fresh_ttl
        self.stale_ttl = stale_ttl
        self.timestamp_key = f"{key}:timestamp"

    def get_cached_data(self) -> Optional[Dict[str, Any]]:
        """
        Retorna dados do cache (frescos ou stale).
        
        Returns:
            Dict com 'data', 'timestamp', 'is_stale' ou None se cache vazio
        """
        try:
            data = cache.get(self.key)
            timestamp = cache.get(self.timestamp_key)

            if data is None:
                return None

            now = time.time()
            age = now - (timestamp or 0)
            is_stale = age > self.fresh_ttl

            return {
                "data": data,
                "timestamp": timestamp,
                "age_seconds": int(age),
                "is_stale": is_stale,
            }
        except Exception:
            logger.exception("Erro ao ler cache SWR para key=%s", self.key)
            return None

    def set_cached_data(self, data: Any) -> None:
        """
        Armazena dados no cache com timestamp.
        
        Args:
            data: Dados para cachear
        """
        try:
            now = time.time()
            cache.set(self.key, data, self.stale_ttl)
            cache.set(self.timestamp_key, now, self.stale_ttl)
            logger.debug(
                "Cache SWR atualizado: key=%s, ttl=%d", self.key, self.stale_ttl
            )
        except Exception:
            logger.exception("Erro ao gravar cache SWR para key=%s", self.key)

    def get_or_fetch(
        self,
        fetch_fn: Callable[[], Any],
        async_task: Optional[Callable] = None,
    ) -> Dict[str, Any]:
        """
        Implementação do padrão SWR.
        
        Lógica:
        1. Se cache fresco → retorna imediatamente
        2. Se cache stale → retorna stale + dispara refresh async
        3. Se cache vazio → faz fetch síncrono
        
        Args:
            fetch_fn: Função síncrona para buscar dados frescos
            async_task: Celery task para refresh assíncrono (opcional)
        
        Returns:
            Dict com 'data', 'timestamp', 'is_stale', 'cache_hit'
        """
        if not SWR_ENABLED:
            # SWR desabilitado: fetch direto
            data = fetch_fn()
            return {
                "data": data,
                "timestamp": time.time(),
                "is_stale": False,
                "cache_hit": False,
            }

        cached = self.get_cached_data()

        if cached is None:
            # Cache vazio: fetch síncrono
            logger.info("Cache SWR miss (vazio): key=%s, fetching sync", self.key)
            data = fetch_fn()
            self.set_cached_data(data)
            return {
                "data": data,
                "timestamp": time.time(),
                "is_stale": False,
                "cache_hit": False,
            }

        if not cached["is_stale"]:
            # Cache fresco: serve imediatamente
            logger.debug("Cache SWR hit (fresco): key=%s, age=%ds", self.key, cached["age_seconds"])
            return {**cached, "cache_hit": True}

        # Cache stale: serve + dispara refresh async
        logger.info(
            "Cache SWR hit (stale): key=%s, age=%ds, triggering background refresh",
            self.key,
            cached["age_seconds"],
        )

        if async_task:
            try:
                async_task()
                logger.debug("Background refresh task dispatched for key=%s", self.key)
            except Exception:
                logger.exception(
                    "Falha ao disparar background refresh para key=%s", self.key
                )

        return {**cached, "cache_hit": True}

    def invalidate(self) -> None:
        """Remove dados do cache."""
        try:
            cache.delete(self.key)
            cache.delete(self.timestamp_key)
            logger.info("Cache SWR invalidado: key=%s", self.key)
        except Exception:
            logger.exception("Erro ao invalidar cache SWR para key=%s", self.key)


# Instância global para dashboard
dashboard_cache = SWRCache(key="dashboard:hosts_status")


def get_dashboard_cached(
    fetch_fn: Callable[[], Dict[str, Any]],
    async_task: Optional[Callable] = None,
) -> Dict[str, Any]:
    """
    Helper para cache SWR do dashboard.
    
    Usage:
        data = get_dashboard_cached(
            fetch_fn=lambda: get_hosts_status_data(),
            async_task=refresh_dashboard_cache_task.delay
        )
    
    Returns:
        Dict com dados + metadata (is_stale, timestamp, etc.)
    """
    return dashboard_cache.get_or_fetch(fetch_fn, async_task)


def invalidate_dashboard_cache() -> None:
    """Invalida cache do dashboard (útil após updates no inventário)."""
    dashboard_cache.invalidate()


__all__ = [
    "SWRCache",
    "dashboard_cache",
    "get_dashboard_cached",
    "invalidate_dashboard_cache",
    "SWR_FRESH_TTL",
    "SWR_STALE_TTL",
    "SWR_ENABLED",
]
