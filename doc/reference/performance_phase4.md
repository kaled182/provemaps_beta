# Fase 4 – Tarefas assíncronas e pré-aquecimento de cache

## 1. Celery configurado
- Adicionadas dependências (`celery==5.4.0`) e criado `core/celery.py` com autodiscovery de tasks.
- `core/__init__.py` expõe `celery_app` para que `celery -A core worker -l info` funcione.
- Ajustes em `core/settings.py`:
  - `CELERY_BROKER_URL` e `CELERY_RESULT_BACKEND` apontam para o Redis (`redis://127.0.0.1:6379/0`).
  - Serializadores e fila padrão definidos para JSON (`mapspro_default`).

## 2. Tarefas de pré-aquecimento (`zabbix_api/tasks.py`)
- `warm_port_optical_cache(port_id)` – revalida e grava no cache o snapshot RX/TX da porta.
- `warm_device_ports(device_id)` – percorre todas as portas do dispositivo.
- `warm_all_optical_snapshots()` – enfileira `warm_port_optical_cache` para todas as portas monitoradas.

## 3. Comando de gerenciamento
```
python manage.py warm_optical_cache [--device-id=<id>] [--async]
```
- Sem `--async` executa inline (bom para pré-aquecer manualmente após o deploy).
- Com `--async` envia as tarefas para o Celery (`warm_port_optical_cache.delay`).
- Exemplo de uso: `python manage.py warm_optical_cache --async` + `celery -A core worker -l info`.

## 4. Resultados pós-aquecimento + Redis
- Após executar `warm_optical_cache` e manter o Redis ativo, o profiling indicou:
  - `port-optical-status`: média ~286 ms / p95 ~1.420 ms (queda adicional na média em relação à fase anterior graças ao cache populado).
  - Demais endpoints mantiveram média <10 ms.
- Rodar o aquecimento periodicamente (via Celery beat ou cron) mantém o cache preenchido e evita que usuários paguem a primeira consulta cara.

## 5. Próximos passos sugeridos
- Configurar um scheduler (Celery Beat/cron) para chamar `warm_all_optical_snapshots` a cada X minutos.
- Monitorar o worker e o Redis (métricas, `redis-cli monitor`).
- Evoluir `port-optical-status` para usar batch de `itemids` se os picos continuarem elevados.
