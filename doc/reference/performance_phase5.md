# Fase 5 – Scheduler e operação contínua

## 1. Celery Beat configurado
- Em `core/settings.py` foi definida a agenda `CELERY_BEAT_SCHEDULE` para executar
  `zabbix_api.tasks.warm_all_optical_snapshots` a cada 10 minutos.
- O schedule usa a mesma fila `mapspro_default`, portanto basta executar:

```bash
celery -A core worker -l info
celery -A core beat -l info
```

(em dois terminais separados ou via supervisão/systemd).

## 2. Tarefa de pré-aquecimento
- A task `warm_all_optical_snapshots` aciona `warm_port_optical_cache` para todas as
  portas, garantindo que os snapshots RX/TX estejam no Redis antes dos usuários acessarem.
- A agenda de 10 minutos pode ser ajustada conforme necessidade (maior frequência =
  menos risco de cache frio).

## 3. Recomendações operacionais
- Monitorar `celery -A core worker -l info` e `celery -A core beat -l info` em logs.
- Verificar métricas do Redis (uso de memória e latência) via `redis-cli info`.
- Em ambientes de produção considerar process supervision (systemd, supervisor, docker compose)
  para manter worker/beat ativos.
- Se quiser customizar o schedule sem alterar código, pode-se integrar `django-celery-beat`
  futuramente.

Com o beat ativo, o cache de potência óptica se mantém aquecido automaticamente, reduzindo
as latências observadas no endpoint `port-optical-status` mesmo sob carga.
