# Fase 3 – Cache e redução de chamadas ao Zabbix

## 1. Cache configurado no Django
- core/settings.py: adicionado CACHES com backend LocMemCache (timeout padrão 60s) e CONN_MAX_AGE permanece 60.
- Optamos por cache em memória local para validar rapidamente os ganhos; em produção recomenda-se substituição por Redis/Memcached.

## 2. Endpoints e funções cacheadas
- pi_fiber_cables agora usa cache.get/set com TTL de 30s.
- pi_device_ports idem (30s).
- _fetch_port_optical_snapshot armazena snapshots RX/TX por porta (30s) quando não há discovery personalizado, reduzindo chamadas repetidas a item.get e history.get.
- 
efreshCableStatusValueMapped continua atualizando o InfoWindow; quando o cache expira, os dados são recarregados.

## 3. Resultados do profiling (MariaDB + cache)
`
python manage.py profile_endpoints --username=perf_tester --password=Perf#2025 --runs=5
`
- ibers: média 1,6 ms / p95 4,8 ms
- sites: média 1,7 ms / p95 2,3 ms
- device-ports: média 7,7 ms / p95 34,3 ms *(antes: 33,4/35,5 ms)*
- port-optical-status: média 252,1 ms / p95 1.253,5 ms *(antes: 351,4/1.749,6 ms)*
- iber-detail: média 2,3 ms / p95 3,1 ms

Observações:
- A média do endpoint port-optical-status reduziu significativamente; os picos remanescentes acontecem quando o cache expira e um novo item.get é necessário. Um cache distribuído ou batch requests deve reduzir ainda mais o p95.
- Logs DEBUG em zabbix_api.services.zabbix_service seguem mostrando a duração de cada chamada ao Zabbix para monitoramento contínuo.

## 4. Próximos passos
- Avaliar Redis/Memcached para cache compartilhado e estratégias de invalidation (ex.: quando cabos/portas forem atualizados).
- Implementar batch das consultas ao Zabbix (agrupar itemids) para mitigar picos.
- Considerar tarefas assíncronas (Celery/RQ) para pré-coletar dados de tráfego e histórico.
