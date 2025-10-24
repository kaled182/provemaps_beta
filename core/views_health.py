import time
import logging
from django.http import JsonResponse
from django.db import connection
from django.core.cache import caches

logger = logging.getLogger(__name__)


def healthz_ready(request):
    """
    Endpoint /ready (Readiness Probe)
    - Propósito: sinalizar ao load balancer/orquestrador que a app está pronta para receber tráfego.
    - Checks leves e rápidos:
        * DB: teste de conexão com SELECT 1 (sem operações pesadas)
        * Cache: obtenção do backend "default" (sem set/get)
    - Retornos:
        * 200 se pronto
        * 503 se alguma dependência crítica falhar
    """
    started = time.time()
    checks = {"db_connected": True, "cache_available": True}

    # DB: conexão leve
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
    except Exception as e:
        checks["db_connected"] = False
        checks["db_error"] = str(e)[:200]

    # Cache: apenas se backend está acessível
    try:
        caches["default"]  # acesso ao backend (sem I/O)
    except Exception as e:
        checks["cache_available"] = False
        checks["cache_error"] = str(e)[:200]

    overall_ready = checks["db_connected"] and checks["cache_available"]
    latency_ms = round((time.time() - started) * 1000, 2)

    if not overall_ready:
        logger.warning("Readiness check not ready", extra={"checks": checks, "latency_ms": latency_ms})

    return JsonResponse(
        {
            "status": "ready" if overall_ready else "not_ready",
            "check": "ready",
            "checks": checks,
            "latency_ms": latency_ms,
            "timestamp": time.time(),
        },
        status=200 if overall_ready else 503,
    )


def healthz_live(request):
    """
    Endpoint /live (Liveness Probe)
    - Propósito: indicar que o processo está vivo (não travou).
    - Deve ser o mais simples possível: se a view respondeu, está vivo.
    - Retorno: sempre 200 (a não ser que o processo esteja realmente quebrado).
    """
    return JsonResponse(
        {
            "status": "alive",
            "check": "live",
            "timestamp": time.time(),
        },
        status=200,
    )
