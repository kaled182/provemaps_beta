"""
Celery app do projeto mapsprovefiber.

- Lê configurações do Django (namespace CELERY_) e cai para env vars quando necessário.
- Define filas/rotas para workloads diferentes (default, zabbix, maps).
- Configura opções sensatas de desempenho e segurança.
"""

import os
import time
from celery import Celery
from kombu import Queue, Exchange

# ---------------------------------------------------------------------
# Bootstrap do Django settings
# ---------------------------------------------------------------------
os.environ.setdefault(
    "DJANGO_SETTINGS_MODULE",
    os.getenv("DJANGO_SETTINGS_MODULE", "settings.dev"),
)

# Nome lógico da app Celery (aparece em logs/monitoramento)
app = Celery("mapsprovefiber")

# Carrega configurações do Django (usa prefixo CELERY_ nas settings)
app.config_from_object("django.conf:settings", namespace="CELERY")

# ---------------------------------------------------------------------
# Fallbacks de broker/backend a partir de variáveis de ambiente
# ---------------------------------------------------------------------
# Prioridade: CELERY_BROKER_URL -> REDIS_URL -> default local
_broker_url = os.getenv("CELERY_BROKER_URL") or os.getenv("REDIS_URL") or "redis://localhost:6379/1"
_result_backend = os.getenv("CELERY_RESULT_BACKEND") or _broker_url

# ---------------------------------------------------------------------
# Opções padrão (podem ser sobrescritas via settings ou env)
# ---------------------------------------------------------------------
app.conf.update(
    broker_url=_broker_url,
    result_backend=_result_backend,

    # Serialização (evita pickle por segurança)
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",

    # Timezone / clock
    timezone=os.getenv("TIME_ZONE", "UTC"),
    enable_utc=True,

    # Confiabilidade / desempenho
    task_acks_late=True,  # evita perder tarefa se o worker cair durante execução
    worker_prefetch_multiplier=int(os.getenv("CELERY_WORKER_PREFETCH_MULTIPLIER", "1")),
    worker_max_tasks_per_child=int(os.getenv("CELERY_WORKER_MAX_TASKS_PER_CHILD", "100")),
    task_soft_time_limit=int(os.getenv("CELERY_TASK_SOFT_TIME_LIMIT", "300")),  # 5 min
    task_time_limit=int(os.getenv("CELERY_TASK_TIME_LIMIT", "600")),            # 10 min
    task_default_rate_limit=os.getenv("CELERY_TASK_DEFAULT_RATE_LIMIT", None),  # ex.: "10/s"
    broker_connection_retry_on_startup=True,

    # Execução síncrona em testes (pode ser definida no env/test)
    task_always_eager=os.getenv("CELERY_TASK_ALWAYS_EAGER", "false").lower() == "true",
    task_eager_propagates=True,

    # Logging mais detalhado
    worker_log_format=os.getenv(
        "CELERY_WORKER_LOG_FORMAT", 
        "[%(asctime)s: %(levelname)s/%(processName)s] %(message)s"
    ),
    worker_task_log_format=os.getenv(
        "CELERY_TASK_LOG_FORMAT",
        "[%(asctime)s: %(levelname)s/%(processName)s] [%(task_name)s(%(task_id)s)] %(message)s"
    ),
    worker_redirect_stdouts=False,
    
    # Retry policies
    task_publish_retry=True,
    task_publish_retry_policy={
        'max_retries': 3,
        'interval_start': 0,
        'interval_step': 0.2,
        'interval_max': 0.2,
    },

    # Monitoring e observabilidade
    worker_send_task_events=True,
    task_send_sent_event=True,
    
    # Result expiration (evita acumular resultados antigos)
    result_expires=int(os.getenv("CELERY_RESULT_EXPIRES", "3600")),  # 1 hora
    
    # Dead letter queue para tarefas que falham repetidamente
    task_reject_on_worker_lost=True,
    task_acks_on_failure_or_timeout=False,
)

# ---------------------------------------------------------------------
# Filas e roteamento
# ---------------------------------------------------------------------
_default_exchange_name = os.getenv("CELERY_DEFAULT_EXCHANGE", "mapsprovefiber")
_default_exchange = Exchange(_default_exchange_name, type="direct")

app.conf.task_queues = (
    Queue("default", _default_exchange, routing_key="default"),
    Queue("zabbix", _default_exchange, routing_key="zabbix"),
    Queue("maps", _default_exchange, routing_key="maps"),
)

app.conf.task_default_queue = os.getenv("CELERY_DEFAULT_QUEUE", "default")
app.conf.task_default_exchange = _default_exchange_name
app.conf.task_default_routing_key = app.conf.task_default_queue

# Regras de roteamento por namespace de tarefa
app.conf.task_routes = {
    # Tarefas do app Zabbix (ex.: zabbix_api/tasks.py -> @shared_task)
    "zabbix_api.tasks.*": {"queue": "zabbix", "routing_key": "zabbix"},

    # Tarefas de rotas/fibra (ex.: routes_builder/tasks.py)
    "routes_builder.tasks.*": {"queue": "maps", "routing_key": "maps"},
}

# ---------------------------------------------------------------------
# Descoberta automática de tasks nos apps instalados
# ---------------------------------------------------------------------
app.autodiscover_tasks()


# ---------------------------------------------------------------------
# Task simples para diagnóstico (útil em health checks de worker)
# ---------------------------------------------------------------------
@app.task(bind=True)
def ping(self):
    """
    Retorna 'pong' — pode ser chamada para sanity-check do worker.
    """
    return "pong"


# ---------------------------------------------------------------------
# Health check mais completo para workers
# ---------------------------------------------------------------------
@app.task(bind=True)
def health_check(self):
    """
    Health check mais completo para workers
    """
    from celery.exceptions import TimeoutError
    
    # Teste básico de funcionamento
    basic_test = "pong"
    
    # Teste de timestamp (verifica se o worker está processando)
    timestamp = time.time()
    
    # Teste opcional de conexão com broker
    broker_ok = True
    broker_error = None
    try:
        # Tenta enviar uma mensagem de teste
        self.app.control.inspect().ping(timeout=2)
    except Exception as e:
        broker_ok = False
        broker_error = str(e)
    
    return {
        "status": "healthy",
        "worker_id": self.request.hostname,
        "timestamp": timestamp,
        "broker_connected": broker_ok,
        "broker_error": broker_error if not broker_ok else None,
        "response": basic_test
    }


# ---------------------------------------------------------------------
# Task para estatísticas das filas (útil para dashboards)
# ---------------------------------------------------------------------
@app.task(bind=True)
def get_queue_stats(self):
    """
    Retorna estatísticas das filas (útil para dashboards)
    """
    try:
        inspector = self.app.control.inspect()
        stats = inspector.stats()
        active = inspector.active()
        scheduled = inspector.scheduled()
        reserved = inspector.reserved()
        
        return {
            "workers": list(stats.keys()) if stats else [],
            "active_tasks": active,
            "scheduled_tasks": scheduled,
            "reserved_tasks": reserved,
            "timestamp": time.time()
        }
    except Exception as e:
        return {"error": str(e), "timestamp": time.time()}